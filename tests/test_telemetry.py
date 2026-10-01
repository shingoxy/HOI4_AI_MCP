"""Protocol and log lifecycle checks; no HOI4 process is needed."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hoi4_operator.telemetry import FrameParser, LogTailer, StateCache, TelemetryService


def frame(seq=706640, *, origin=0, pp="52.3", date="23:00, 1 January, 1936"):
    return [
        f"[game] CODEX_STATE_BEGIN|version=1|seq={seq}|origin={origin}",
        (f"[game] CODEX|date={date}|tag=GER|political_power={pp}"
         "|stability=0.9|war_support=0.5|manpower_k=1280"
         "|civilian_factories=30|military_factories=28|dockyards=10"),
        f"[game] CODEX_STATE_END|seq={seq}",
    ]


def feed(parser, lines):
    result = None
    for line in lines:
        next_state = parser.feed(line)
        if next_state is not None:
            result = next_state
    return result


class ParserTests(unittest.TestCase):
    def test_complete_frame_and_unrelated_lines(self):
        parser = FrameParser()
        lines = ["ordinary HOI4 log", frame()[0], "other warning", *frame()[1:]]
        state = feed(parser, lines)
        self.assertEqual(state.seq, 706640)
        self.assertEqual(state.country, "GER")
        self.assertEqual(state.manpower.available, 1280000)
        self.assertEqual(state.industry.military_factories, 28)
        self.assertEqual(len(parser.errors), 0)

    def test_missing_end_does_not_commit(self):
        parser = FrameParser()
        self.assertIsNone(feed(parser, frame()[:-1]))
        self.assertIsNone(parser.feed(frame(706641)[0]))
        self.assertIn("incomplete frame", parser.errors[-1])

    def test_sequence_mismatch(self):
        parser = FrameParser()
        lines = frame()
        lines[-1] = "CODEX_STATE_END|seq=706641"
        self.assertIsNone(feed(parser, lines))
        self.assertIn("sequence mismatch", parser.errors[-1])

    def test_malformed_value_and_duplicate_field(self):
        parser = FrameParser()
        self.assertIsNone(feed(parser, frame(pp="oops")))
        self.assertTrue(parser.errors)
        lines = frame()
        lines[1] += "|political_power=1"
        self.assertIsNone(feed(parser, lines))
        self.assertIn("duplicate", parser.errors[-1])

    def test_orphan_end_records_error_and_next_frame_recovers(self):
        parser = FrameParser()
        self.assertIsNone(parser.feed("CODEX_STATE_END|seq=706640"))
        self.assertIn("END without complete frame", parser.errors[-1])
        self.assertEqual(feed(parser, frame()).seq, 706640)

    def test_duplicate_and_older_sequence_do_not_replace_cache(self):
        parser = FrameParser()
        cache = StateCache()
        first = feed(parser, frame())
        self.assertTrue(cache.update(first))
        self.assertFalse(cache.update(feed(parser, frame())))
        newer = feed(parser, frame(706641, pp="54"))
        self.assertTrue(cache.update(newer))
        self.assertFalse(cache.update(feed(parser, frame(706640, pp="1"))))
        self.assertEqual(cache.latest_state.politics.political_power, 54)

    def test_startup_allows_save_load_rewind(self):
        parser = FrameParser()
        cache = StateCache()
        cache.update(feed(parser, frame(706645)))
        self.assertTrue(cache.update(feed(parser, frame(706640, origin=1, pp="40"))))
        self.assertEqual(cache.latest_seq, 706640)
        self.assertEqual(cache.latest_state.politics.political_power, 40)

    def test_daily_save_load_rewind_recovers_after_two_days(self):
        parser = FrameParser()
        cache = StateCache()
        cache.update(feed(parser, frame(706650, date="23:00, 11 January, 1936")))
        first = feed(parser, frame(706640, pp="40"))
        self.assertFalse(cache.update(first))
        self.assertEqual(cache.latest_seq, 706650)
        second = feed(parser, frame(706641, pp="41", date="23:00, 2 January, 1936"))
        self.assertTrue(cache.update(second))
        self.assertEqual(cache.latest_seq, 706641)
        self.assertEqual(cache.game_date, "23:00, 2 January, 1936")
        self.assertFalse(cache.update(feed(parser, frame(706640, pp="1"))))

    def test_fresh_stale_unavailable(self):
        cache = StateCache()
        self.assertEqual(cache.freshness(), "unavailable")
        stamp = datetime.now(timezone.utc)
        cache.update(feed(FrameParser(), frame()), received_at=stamp)
        self.assertEqual(cache.freshness(now=stamp), "fresh")
        self.assertEqual(cache.freshness(now=stamp + timedelta(seconds=31)), "stale")


class TailerTests(unittest.TestCase):
    def test_partial_line_and_truncate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.log"
            path.write_bytes(b"first\npartial")
            tailer = LogTailer(path, start_at_end=False)
            self.assertEqual(tailer.poll(), ["first"])
            with path.open("ab") as handle:
                handle.write(b" line\n")
            self.assertEqual(tailer.poll(), ["partial line"])
            path.write_bytes(b"new\n")
            self.assertEqual(tailer.poll(), ["new"])

    def test_recreated_file_and_initially_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.log"
            tailer = LogTailer(path)
            self.assertEqual(tailer.poll(), [])
            path.write_bytes(b"created\n")
            self.assertEqual(tailer.poll(), ["created"])
            path.replace(Path(folder) / "old.log")
            path.write_bytes(b"recreated\n")
            self.assertEqual(tailer.poll(), ["recreated"])

    def test_service_keeps_only_complete_latest_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.log"
            path.write_text("\n".join(frame() + frame(706641)[:2]) + "\n", encoding="utf-8")
            service = TelemetryService(path, start_at_end=False)
            self.assertEqual(service.poll(), 1)
            self.assertEqual(service.get_summary()["latest_seq"], 706640)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(frame(706641)[2] + "\n")
            self.assertEqual(service.poll(), 1)
            self.assertEqual(service.get_summary()["latest_seq"], 706641)

    def test_partial_end_and_recreated_log_reset_service(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.log"
            path.write_text("\n".join(frame(706650)[:2]) + "\nCODEX_STATE_END|seq=706650", encoding="utf-8")
            service = TelemetryService(path, start_at_end=False)
            self.assertEqual(service.poll(), 0)
            self.assertIsNone(service.cache.latest_state)
            with path.open("a", encoding="utf-8") as handle:
                handle.write("\n")
            self.assertEqual(service.poll(), 1)
            path.replace(Path(folder) / "old.log")
            path.write_text("\n".join(frame(706640, origin=1)) + "\n", encoding="utf-8")
            self.assertEqual(service.poll(), 1)
            self.assertEqual(service.cache.latest_seq, 706640)


class DiagnosticTests(unittest.TestCase):
    def test_read_only_command_reports_latest_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.log"
            path.write_text("\n".join(frame()) + "\n", encoding="utf-8")
            command = Path(__file__).resolve().parents[1] / "scripts" / "check_telemetry.py"
            completed = subprocess.run(
                [sys.executable, str(command), "--log", str(path)],
                capture_output=True, text=True, check=True,
            )
            result = json.loads(completed.stdout)
            self.assertTrue(result["log_exists"])
            self.assertEqual((result["begin_count"], result["end_count"]), (1, 1))
            self.assertEqual(result["latest_seq"], 706640)
            self.assertEqual(result["latest_game_date"], "23:00, 1 January, 1936")
            self.assertEqual(result["latest_state"]["politics"]["political_power"], 52.3)
            self.assertEqual(result["parser_errors"], [])

    def test_missing_log_and_malformed_frame_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.log"
            command = Path(__file__).resolve().parents[1] / "scripts" / "check_telemetry.py"
            missing = subprocess.run(
                [sys.executable, str(command), "--log", str(path)],
                capture_output=True, text=True, check=True,
            )
            self.assertFalse(json.loads(missing.stdout)["log_exists"])
            path.write_text("\n".join(frame(pp="invalid")) + "\n", encoding="utf-8")
            malformed = subprocess.run(
                [sys.executable, str(command), "--log", str(path)],
                capture_output=True, text=True, check=True,
            )
            result = json.loads(malformed.stdout)
            self.assertEqual((result["begin_count"], result["end_count"]), (1, 1))
            self.assertIsNone(result["latest_seq"])
            self.assertTrue(result["parser_errors"])


if __name__ == "__main__":
    unittest.main()

"""Changes and freshness across replay, daily updates and log reset."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_telemetry import frame
from hoi4_operator.read_model import ReadModel


def append(path, *frames):
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(line for lines in frames for line in lines) + "\n")


class ReadModelTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "game.log"

    def test_replay_is_stale_baseline_and_queries_do_not_write(self):
        append(self.path, frame())
        old = (datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()
        os.utime(self.path, (old, old))
        before = self.path.read_bytes(), self.path.stat().st_mtime_ns
        model = ReadModel(self.path)
        self.assertEqual(model.summary()["status"], "stale")
        self.assertEqual(model.summary()["freshness_basis"], "log_mtime_upper_bound")
        self.assertEqual(model.changes()["events"], [])
        self.assertEqual(model.section("industry")["production_lines"]["status"], "UNKNOWN")
        self.assertFalse(model.poll())
        self.assertEqual(before, (self.path.read_bytes(), self.path.stat().st_mtime_ns))

    def test_each_frame_in_batch_is_recorded_and_duplicate_ignored(self):
        append(self.path, frame())
        model = ReadModel(self.path)
        append(self.path, frame(), frame(706641, pp="54"), frame(706642, pp="55"))
        self.assertTrue(model.poll())
        events = model.changes()["events"]
        self.assertEqual([e["seq"] for e in events], [706641, 706642])
        self.assertEqual(events[0]["fields"]["politics.political_power"], {"before": 52.3, "after": 54})
        self.assertEqual(model.summary()["status"], "fresh")
        self.assertEqual(model.summary()["freshness_basis"], "frame_received_at")
        self.assertFalse(model.poll())
        self.assertEqual(len(model.changes()["events"]), 2)

    def test_rollback_is_timeline_reset_without_false_gameplay_delta(self):
        append(self.path, frame(706650))
        model = ReadModel(self.path)
        append(self.path, frame(706640, pp="1"))
        self.assertFalse(model.poll())
        self.assertEqual(model.revision, 0)
        append(self.path, frame(706641, pp="2", date="2 January, 1936"))
        self.assertTrue(model.poll())
        event = model.changes()["events"][0]
        self.assertEqual(event["kind"], "timeline_reset")
        self.assertEqual(event["fields"], {})
        self.assertEqual(model.summary()["latest_seq"], 706641)

    def test_missing_and_recreated_log_do_not_compare_across_generations(self):
        append(self.path, frame(706650))
        model = ReadModel(self.path)
        self.path.unlink()
        self.assertTrue(model.poll())
        self.assertEqual(model.summary()["status"], "unavailable")
        append(self.path, frame(706640, origin=1))
        self.assertTrue(model.poll())
        self.assertEqual([e["kind"] for e in model.changes()["events"]], ["log_reset", "state_updated"])
        self.assertEqual(model.changes()["events"][-1]["fields"], {})

    def test_read_failure_is_visible_and_recovery_does_not_replay(self):
        append(self.path, frame())
        model = ReadModel(self.path)
        with patch.object(Path, "open", side_effect=PermissionError("read denied")):
            self.assertTrue(model.poll())
            self.assertEqual(model.summary()["status"], "unavailable")
            self.assertIn("read denied", model.diagnostics()["log_read_error"])
        self.assertTrue(model.poll())
        self.assertEqual(model.revision, 0)

    def test_freshness_transition_notifies_once_and_history_is_bounded(self):
        append(self.path, frame())
        model = ReadModel(self.path)
        model.service.cache.received_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.assertTrue(model.poll())
        self.assertFalse(model.poll())
        append(self.path, *(frame(seq, pp=str(seq)) for seq in range(706641, 706746)))
        model.poll()
        self.assertEqual(len(model.changes()["events"]), 100)
        self.assertTrue(model.changes()["history_truncated"])
        self.assertFalse(model.changes(model.revision - 1)["history_truncated"])
        with self.assertRaises(ValueError):
            model.changes(model.revision + 1)
        with self.assertRaises(ValueError):
            model.changes(True)


if __name__ == "__main__":
    unittest.main()

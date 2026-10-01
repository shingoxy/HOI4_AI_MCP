"""Protocol v2 boundaries and v1/v2 transitions; no game actions."""

from pathlib import Path
import re
import tempfile
import unittest

from test_telemetry import feed, frame
from test_read_model import append
from hoi4_operator.read_model import ReadModel
from hoi4_operator.telemetry import FrameParser, StateCache
from hoi4_operator.telemetry.parser import TRACKED_TECHS


def extended_frame(seq=706640, **overrides):
    lines = frame(seq, date=f"day {seq}")
    lines[0] = lines[0].replace("version=1", "version=2")
    fields = {"research_slots": "4", "focus_completed": "0",
              "focus_progress_lower": "0.2", "focus_progress_upper": "0.3"}
    for tech in TRACKED_TECHS:
        fields[f"researching_{tech}"] = "0"
        fields[f"researched_{tech}"] = "0"
    fields.update(overrides)
    lines[1] += "".join(f"|{key}={value}" for key, value in fields.items())
    return lines


class ExtendedParserTests(unittest.TestCase):
    def test_typed_research_and_focus_without_claiming_current_focus(self):
        state = feed(FrameParser(), extended_frame(researching_construction1="1"))
        self.assertEqual(state.protocol_version, 2)
        self.assertEqual(state.research.slot_count, 4)
        self.assertEqual(state.research.tracked_technologies[1].tech_id, "construction1")
        self.assertTrue(state.research.tracked_technologies[1].researching)
        self.assertEqual((state.focus.progress_lower_bound, state.focus.progress_upper_bound), (0.2, 0.3))
        self.assertFalse(state.focus.completed)
        completed = feed(FrameParser(), extended_frame(
            focus_completed="1", focus_progress_lower="1", focus_progress_upper="1"))
        self.assertTrue(completed.focus.completed)
        legacy = feed(FrameParser(), frame())
        self.assertIsNone(legacy.research)
        self.assertIsNone(legacy.focus)

    def test_invalid_extended_fields_never_replace_valid_cache(self):
        cache = StateCache()
        parser = FrameParser()
        cache.update(feed(parser, extended_frame()))
        invalid = [
            {"research_slots": "-1"}, {"research_slots": "1.5"},
            {"researching_construction1": "2"},
            {"researching_construction1": "1", "researched_construction1": "1"},
            {"research_slots": "0", "researching_construction1": "1"},
            {"focus_progress_lower": "0.4", "focus_progress_upper": "0.3"},
            {"focus_progress_lower": "0.25", "focus_progress_upper": "0.35"},
            {"focus_progress_upper": "0.9"},
            {"focus_completed": "1"}, {"focus_progress_upper": "NaN"},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                self.assertIsNone(feed(parser, extended_frame(706641, **overrides)))
                self.assertEqual(cache.latest_seq, 706640)
                self.assertTrue(parser.errors)

    def test_missing_duplicate_half_frame_and_unknown_version(self):
        for modify in (lambda x: x[1].replace("|research_slots=4", ""),
                       lambda x: x[1] + "|research_slots=4"):
            lines = extended_frame()
            lines[1] = modify(lines)
            self.assertIsNone(feed(FrameParser(), lines))
        self.assertIsNone(feed(FrameParser(), extended_frame()[:2]))
        lines = extended_frame()
        lines[0] = lines[0].replace("version=2", "version=3")
        parser = FrameParser()
        self.assertIsNone(feed(parser, lines))
        self.assertIn("unsupported protocol", parser.errors[-1])

    def test_mod_log_templates_match_the_parser_contract(self):
        source = (Path(__file__).resolve().parents[1] / "mod/codex_telemetry/common/scripted_effects/codex_telemetry.txt").read_text(encoding="utf-8")
        templates = re.findall(r'log = "([^"]+)"', source)
        expected = extended_frame()
        values = dict(part.split("=", 1) for part in expected[1].split("CODEX|", 1)[1].split("|"))
        replacements = {
            "codex_seq": "706640", "codex_origin": "0", "codex_pp": values["political_power"],
            "codex_stability": values["stability"], "codex_war_support": values["war_support"],
            "codex_manpower_k": values["manpower_k"], "codex_civ": values["civilian_factories"],
            "codex_mil": values["military_factories"], "codex_dock": values["dockyards"],
            "codex_research_slots": "4", "codex_focus_completed": "0",
            "codex_focus_lower": "0.2", "codex_focus_upper": "0.3",
        }
        for index in range(3):
            replacements[f"codex_researching_{index}"] = "0"
            replacements[f"codex_researched_{index}"] = "0"
        emitted = [re.sub(r'\[\?([a-z0-9_]+)\]', lambda m: replacements[m[1]], line)
                   .replace("[GetDateText]", "day 706640").replace("[THIS.GetTag]", "GER") for line in templates]
        self.assertEqual(feed(FrameParser(), emitted), feed(FrameParser(), expected))


class ExtendedReadModelTests(unittest.TestCase):
    def test_protocol_upgrade_downgrade_records_fields_and_unavailable_sections(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.log"
            append(path, frame())
            model = ReadModel(path)
            self.assertEqual(model.section("research")["section_status"], "unavailable")
            append(path, extended_frame(706641, researching_construction1="1"))
            self.assertTrue(model.poll())
            self.assertEqual(model.section("research")["research"]["slot_count"], 4)
            self.assertNotIn("research_slots", model.diagnostics()["unknown_fields"])
            self.assertEqual(model.section("focus")["current_focus"]["status"], "UNKNOWN")
            self.assertEqual(model.changes()["events"][-1]["fields"]["research.slot_count"], {"before": None, "after": 4})
            append(path, frame(706642))
            self.assertTrue(model.poll())
            self.assertEqual(model.section("focus")["section_status"], "unavailable")
            self.assertIn("research_slots", model.diagnostics()["unknown_fields"])


if __name__ == "__main__":
    unittest.main()

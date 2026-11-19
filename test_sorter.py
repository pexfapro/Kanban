"""Offline tests for sorter.py. Run: python3 -m unittest -v"""

import datetime as dt
import io
import json
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock
from pathlib import Path

import sorter

CONFIG = json.loads(Path(__file__).with_name("config.json").read_text())
FIXTURE = Path(__file__).with_name("fixtures") / "routine_sample.json"

THU = dt.date(2026, 11, 19)   # weekly pattern: wfh
FRI = dt.date(2026, 11, 20)   # weekly pattern: office
SAT = dt.date(2026, 11, 21)   # weekly pattern: off

SECTIONS = [
    {"id": "s_habits", "name": "Habits"},
    {"id": "s_any", "name": "Anytime"},
    {"id": "s_morn", "name": "Morning"},
    {"id": "s_aft", "name": "Afternoon"},
    {"id": "s_eve", "name": "Evening"},
    {"id": "s_wind", "name": "Wind down"},
    {"id": "s_not", "name": "Not today"},
]


def task(content, description="", section_id=None, due=None, **extra):
    t = {"id": content, "content": content, "description": description,
         "section_id": section_id, "parent_id": None,
         "due": {"date": due} if due else None}
    t.update(extra)
    return t


def moves(actions):
    return {a.task["content"]: a.section for a in actions if a.kind == "move"}


class ParseSlotLine(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(
            sorter.parse_slot_line("office: evening | wfh: afternoon | off: morning"),
            {"office": "evening", "wfh": "afternoon", "off": "morning"})

    def test_emoji_case_and_middle_dot(self):
        self.assertEqual(
            sorter.parse_slot_line("🏢: Evening · 🏠 : Wind-Down · 🌴: SKIP"),
            {"office": "evening", "wfh": "wind down", "off": "skip"})

    def test_found_among_other_lines(self):
        desc = "Some notes\n\n- a list\nOFFICE: Morning | WFH: anytime\nmore text"
        self.assertEqual(sorter.parse_slot_line(desc),
                         {"office": "morning", "wfh": "anytime"})

    def test_no_slot_line(self):
        self.assertIsNone(sorter.parse_slot_line(""))
        self.assertIsNone(sorter.parse_slot_line(None))
        self.assertIsNone(sorter.parse_slot_line("Note: office is closed"))
        self.assertIsNone(sorter.parse_slot_line("1. Reconcile transactions"))

    def test_bad_value_dropped_with_warning(self):
        slots = sorter.parse_slot_line("office: lunchtime | wfh: evening")
        self.assertEqual(slots, {"wfh": "evening"})
        self.assertEqual(len(slots.warnings), 1)


class ResolveDayType(unittest.TestCase):
    def test_weekly_pattern(self):
        self.assertEqual(sorter.resolve_day_type([], THU, CONFIG)[0], "wfh")
        self.assertEqual(sorter.resolve_day_type([], FRI, CONFIG)[0], "office")
        self.assertEqual(sorter.resolve_day_type([], SAT, CONFIG)[0], "off")

    def test_override_due_today_wins(self):
        tasks = [task("Day: off", due="2026-11-19")]
        day_type, source = sorter.resolve_day_type(tasks, THU, CONFIG)
        self.assertEqual(day_type, "off")
        self.assertIn("override", source)

    def test_override_for_other_day_ignored(self):
        tasks = [task("Day: off", due="2026-11-20"),
                 task("Day: office", due="2026-11-18")]
        self.assertEqual(sorter.resolve_day_type(tasks, THU, CONFIG)[0], "wfh")

    def test_latest_override_wins(self):
        tasks = [task("Day: off", due="2026-11-19", added_at="2026-11-01T00:00:00Z"),
                 task("day:OFFICE", due="2026-11-19", added_at="2026-11-10T00:00:00Z")]
        self.assertEqual(sorter.resolve_day_type(tasks, THU, CONFIG)[0], "office")


class Plan(unittest.TestCase):
    LINE = "office: evening | wfh: afternoon | off: skip"

    def test_moves_to_slot_for_day_type(self):
        tasks = [task("YNAB", self.LINE, section_id="s_habits")]
        self.assertEqual(moves(sorter.plan(tasks, SECTIONS, "office", FRI)[0]),
                         {"YNAB": "Evening"})
        self.assertEqual(moves(sorter.plan(tasks, SECTIONS, "wfh", THU)[0]),
                         {"YNAB": "Afternoon"})
        self.assertEqual(moves(sorter.plan(tasks, SECTIONS, "off", SAT)[0]),
                         {"YNAB": "Not today"})

    def test_task_with_no_section_is_moved(self):
        tasks = [task("YNAB", self.LINE, section_id=None)]
        self.assertEqual(moves(sorter.plan(tasks, SECTIONS, "wfh", THU)[0]),
                         {"YNAB": "Afternoon"})

    def test_idempotent(self):
        tasks = [task("YNAB", self.LINE, section_id="s_aft")]
        self.assertEqual(sorter.plan(tasks, SECTIONS, "wfh", THU)[0], [])

    def test_ignored_tasks(self):
        tasks = [task("No line", "just notes", section_id="s_habits"),
                 task("Sub", self.LINE, section_id="s_habits", parent_id="p1"),
                 task("Partial", "office: morning", section_id="s_habits")]
        actions, notes, _ = sorter.plan(tasks, SECTIONS, "wfh", THU)
        self.assertEqual(actions, [])
        self.assertTrue(any("Partial" in n and "no slot for wfh" in n for n in notes))

    def test_override_tasks_parked_and_expired_deleted(self):
        tasks = [task("Day: off", due="2026-11-19"),       # today
                 task("Day: wfh", due="2026-11-25"),       # future
                 task("Day: office", due="2026-11-18")]    # past
        actions, _, _ = sorter.plan(tasks, SECTIONS, "off", THU)
        self.assertEqual(moves(actions), {"Day: off": "Not today",
                                          "Day: wfh": "Not today"})
        deleted = [a.task["content"] for a in actions if a.kind == "delete"]
        self.assertEqual(deleted, ["Day: office"])

    def test_missing_not_today_section_stops(self):
        sections = [s for s in SECTIONS if s["name"] != "Not today"]
        with self.assertRaises(SystemExit):
            sorter.plan([], sections, "wfh", THU)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            sorter.main(["--fixture", str(FIXTURE), *args])
        return out.getvalue()

    def test_fixture_run_is_dry_and_reports_day_type(self):
        out = self.run_cli("--date", "2026-11-19")
        self.assertIn("[DRY RUN]", out)
        self.assertIn("day type WFH from weekly pattern (thu)", out)
        self.assertIn("'Daily Processing': Habits -> Afternoon", out)

    def test_fixture_office_day_parks_daily_processing(self):
        out = self.run_cli("--date", "2026-11-20")
        self.assertIn("'Daily Processing': Habits -> Not today", out)



class Retry(unittest.TestCase):
    """The API client retries brief Todoist outages (fake network, no sleep)."""

    def call(self, responses, method="GET"):
        calls = []

        def fake_urlopen(req, timeout):
            calls.append(req)
            r = responses.pop(0)
            if isinstance(r, Exception):
                raise r
            return io.BytesIO(r)

        err = io.StringIO()
        with mock.patch("urllib.request.urlopen", fake_urlopen), \
             mock.patch("time.sleep"), redirect_stderr(err):
            result = sorter.Todoist("t")._request(method, "/x")
        return result, len(calls)

    @staticmethod
    def http(code):
        return urllib.error.HTTPError("u", code, "err", {}, io.BytesIO(b""))

    def test_server_error_then_success(self):
        result, n = self.call([self.http(502), self.http(503), b'{"ok": 1}'])
        self.assertEqual((result, n), ({"ok": 1}, 3))

    def test_network_error_retried(self):
        result, n = self.call([urllib.error.URLError("reset"), b"{}"])
        self.assertEqual((result, n), ({}, 2))

    def test_gives_up_after_all_attempts(self):
        with self.assertRaises(SystemExit):
            self.call([self.http(503)] * (len(sorter.RETRY_WAITS) + 1))

    def test_client_error_not_retried(self):
        with self.assertRaises(SystemExit):
            self.call([self.http(403), b"{}"])

    def test_repeat_delete_404_counts_as_done(self):
        result, n = self.call([self.http(502), self.http(404)], "DELETE")
        self.assertEqual((result, n), (None, 2))


class StatusCard(unittest.TestCase):
    def card(self, content):
        return task(content, sorter.STATUS_DESCRIPTION)

    def test_title(self):
        self.assertEqual(sorter.status_title("wfh", THU, False),
                         "* 🏠 WFH day · Thu 19 Nov (weekly pattern)")
        self.assertEqual(sorter.status_title("off", FRI, True),
                         "* 🌴 Off day · Fri 20 Nov (override)")

    def test_created_when_missing(self):
        a = sorter.plan_status([task("YNAB")], "office", FRI, False)
        self.assertEqual((a.kind, a.content),
                         ("status-create", "* 🏢 Office day · Fri 20 Nov (weekly pattern)"))

    def test_retitled_when_stale_and_left_when_current(self):
        stale = self.card("* 🏠 WFH day · Thu 19 Nov (weekly pattern)")
        a = sorter.plan_status([stale], "office", FRI, False)
        self.assertEqual((a.kind, a.task, a.content),
                         ("status-update", stale,
                          "* 🏢 Office day · Fri 20 Nov (weekly pattern)"))
        self.assertIsNone(sorter.plan_status([stale], "wfh", THU, False))

    def test_never_moved_by_planner(self):
        card = self.card("* 🏠 WFH day · Thu 19 Nov (weekly pattern)")
        card["description"] += "\noffice: morning | wfh: morning | off: morning"
        self.assertEqual(sorter.plan([card], SECTIONS, "wfh", THU)[0], [])

    def test_cli_reports_status(self):
        out = io.StringIO()
        with redirect_stdout(out):
            sorter.main(["--fixture", str(FIXTURE), "--date", "2026-11-21"])
        self.assertIn("status  create '* 🌴 Off day · Sat 21 Nov (weekly pattern)'",
                      out.getvalue())


if __name__ == "__main__":
    unittest.main()

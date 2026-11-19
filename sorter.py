#!/usr/bin/env python3
"""Day-type routine sorter for Todoist.

Moves each task in the Routine project into the section that matches today's
day type (office / wfh / off). See DESIGN.md for the rules.

Usage:
    python3 sorter.py                      # today, live Todoist data
    python3 sorter.py --date 2026-11-21    # pretend it's another day
    python3 sorter.py --fixture data.json  # offline, no API calls

Environment:
    TODOIST_API_TOKEN  Todoist API token (not needed with --fixture).
    DRY_RUN            "1" (default) prints planned moves only.
                       "0" makes the moves and deletions for real.

Standard library only.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

API_BASE = "https://api.todoist.com/api/v1"
NOT_TODAY = "Not today"
RETRY_WAITS = (5, 15, 45)  # seconds between attempts on a transient error
DAY_TYPES = ("office", "wfh", "off")
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

# Keys accepted in a slot line, mapped to a day type.
KEY_ALIASES = {"office": "office", "wfh": "wfh", "off": "off",
               "🏢": "office", "🏠": "wfh", "🌴": "off"}
# Slot values, mapped to the Todoist section name they mean.
SLOT_SECTIONS = {"morning": "Morning", "afternoon": "Afternoon",
                 "evening": "Evening", "wind down": "Wind down",
                 "anytime": "Anytime", "skip": NOT_TODAY}

_KEY_RE = "|".join(re.escape(k) for k in KEY_ALIASES)
_SEGMENT_RE = re.compile(rf"^\s*({_KEY_RE})\s*:\s*(.+?)\s*$", re.IGNORECASE)
_SEPARATOR_RE = re.compile(r"\s*[|·]\s*")
_OVERRIDE_RE = re.compile(r"^\s*day\s*:\s*(office|wfh|off)\s*$", re.IGNORECASE)


# ---------------------------------------------------------------- parsing

def _normalise_slot(value):
    """'Wind-down', 'winddown', ' WIND  down ' -> 'wind down'."""
    v = re.sub(r"[\s_-]+", " ", value.strip().lower())
    return "wind down" if v == "winddown" else v


def parse_slot_line(description):
    """Return {day_type: slot} from the first slot line in a description.

    A slot line is a line made only of `key: value` segments separated by
    `|` (or `·`), e.g. `office: evening | wfh: afternoon | off: morning`.
    Returns None if the description has no slot line. Segments with an
    unknown slot value are dropped, with a warning collected in `.warnings`.
    """
    for line in (description or "").splitlines():
        segments = [s for s in _SEPARATOR_RE.split(line.strip()) if s]
        if not segments:
            continue
        matches = [_SEGMENT_RE.match(s) for s in segments]
        if not all(matches):
            continue
        slots, warnings = {}, []
        for m in matches:
            day_type = KEY_ALIASES[m.group(1).lower()]
            slot = _normalise_slot(m.group(2))
            if slot in SLOT_SECTIONS:
                slots[day_type] = slot
            else:
                warnings.append(f"unknown slot '{m.group(2)}' for {day_type}")
        return SlotLine(slots, warnings)
    return None


class SlotLine(dict):
    """A dict of {day_type: slot} that also carries parse warnings."""

    def __init__(self, slots, warnings):
        super().__init__(slots)
        self.warnings = warnings


def override_day_type(task):
    """'Day: wfh' -> 'wfh'; anything else -> None."""
    m = _OVERRIDE_RE.match(task.get("content") or "")
    return m.group(1).lower() if m else None


def due_date(task):
    """The task's due date as a date, or None. Handles '2026-11-21T07:15:00'."""
    due = task.get("due") or {}
    raw = due.get("date")
    return dt.date.fromisoformat(raw[:10]) if raw else None


# ---------------------------------------------------------------- logic

def resolve_day_type(tasks, today, config):
    """Return (day_type, source) for `today`.

    An override task `Day: office|wfh|off` due today wins; otherwise the
    weekly pattern in config.json. If several overrides are due today, the
    most recently added one wins.
    """
    todays = [t for t in tasks
              if override_day_type(t) and due_date(t) == today]
    if todays:
        todays.sort(key=lambda t: t.get("added_at") or "")
        chosen = todays[-1]
        return override_day_type(chosen), f"override task '{chosen['content']}'"
    weekday = WEEKDAYS[today.weekday()]
    return config["week"][weekday], f"weekly pattern ({weekday})"


@dataclass
class Action:
    kind: str          # "move" or "delete"
    task: dict
    section: str = ""  # target section name, for moves
    reason: str = ""


def plan(tasks, sections, day_type, today):
    """Work out what to change. Pure: no API calls.

    Returns (actions, notes, section_names_by_id). `notes` are warnings and
    skipped tasks worth printing. Raises SystemExit if the Not today
    section is missing.
    """
    by_name = {s["name"].strip().lower(): s for s in sections}
    by_id = {s["id"]: s["name"] for s in sections}
    if NOT_TODAY.lower() not in by_name:
        raise SystemExit(f"Section '{NOT_TODAY}' not found in the project. "
                         "Create it in Todoist (last on the board) and re-run.")

    actions, notes = [], []

    def move_to(task, section_name, reason):
        target = by_name.get(section_name.lower())
        if target is None:
            notes.append(f"'{task['content']}': section '{section_name}' "
                         "not found, left where it is")
        elif task.get("section_id") != target["id"]:
            actions.append(Action("move", task, target["name"], reason))

    for task in tasks:
        title = task.get("content", "")
        if task.get("parent_id"):
            continue  # subtasks follow their parent

        override = override_day_type(task)
        if override:
            when = due_date(task)
            if when and when < today:
                actions.append(Action("delete", task,
                                      reason=f"override for {when} has passed"))
            else:
                if when is None:
                    notes.append(f"'{title}': override task has no due date")
                move_to(task, NOT_TODAY, "override task")
            continue

        slots = parse_slot_line(task.get("description"))
        if slots is None:
            continue  # not managed by the sorter
        for w in slots.warnings:
            notes.append(f"'{title}': {w}")
        slot = slots.get(day_type)
        if slot is None:
            notes.append(f"'{title}': no slot for {day_type}, left where it is")
            continue
        move_to(task, SLOT_SECTIONS[slot], f"{day_type}: {slot}")

    return actions, notes, by_id


# ---------------------------------------------------------------- Todoist API

class Todoist:
    def __init__(self, token):
        self.token = token

    def _request(self, method, path, params=None, body=None):
        url = f"{API_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })
        # Todoist sometimes returns a brief 502/503 (seen at go-live). Retry
        # server errors, rate limits and network failures before giving up.
        # Every call is safe to repeat: a move to the section a task is
        # already in changes nothing, and a repeated delete gets a 404.
        for attempt, wait in enumerate(RETRY_WAITS + (None,)):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                return json.loads(raw) if raw else None
            except urllib.error.HTTPError as e:
                if method == "DELETE" and e.code == 404 and attempt > 0:
                    return None  # an earlier attempt deleted it
                retryable = e.code == 429 or e.code >= 500
                error = f"HTTP {e.code} {e.read().decode(errors='replace')[:300]}"
            except (urllib.error.URLError, TimeoutError) as e:
                retryable, error = True, str(e)
            if not retryable or wait is None:
                raise SystemExit(f"Todoist API {method} {path} failed: {error}")
            print(f"  retry   {method} {path}: {error.strip()}; "
                  f"waiting {wait}s", file=sys.stderr)
            time.sleep(wait)

    def _list(self, path, params):
        """GET a paginated list endpoint ({results, next_cursor})."""
        items, cursor = [], None
        while True:
            p = dict(params, limit=200)
            if cursor:
                p["cursor"] = cursor
            page = self._request("GET", path, p)
            items += page["results"]
            cursor = page.get("next_cursor")
            if not cursor:
                return items

    def sections(self, project_id):
        return self._list("/sections", {"project_id": project_id})

    def tasks(self, project_id):
        return self._list("/tasks", {"project_id": project_id})

    def move(self, task_id, section_id):
        self._request("POST", f"/tasks/{task_id}/move",
                      body={"section_id": section_id})

    def delete(self, task_id):
        self._request("DELETE", f"/tasks/{task_id}")


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", type=dt.date.fromisoformat,
                    help="treat this date (YYYY-MM-DD) as today")
    ap.add_argument("--fixture", type=Path,
                    help="read sections and tasks from this JSON file "
                         "instead of Todoist (implies dry run)")
    ap.add_argument("--config", type=Path,
                    default=Path(__file__).with_name("config.json"))
    args = ap.parse_args(argv)

    config = json.loads(args.config.read_text())
    today = args.date or dt.datetime.now(ZoneInfo(config["timezone"])).date()
    dry_run = os.environ.get("DRY_RUN", "1") != "0" or args.fixture is not None

    if args.fixture:
        data = json.loads(args.fixture.read_text())
        api, sections, tasks = None, data["sections"], data["tasks"]
    else:
        token = os.environ.get("TODOIST_API_TOKEN")
        if not token:
            raise SystemExit("TODOIST_API_TOKEN is not set.")
        api = Todoist(token)
        sections = api.sections(config["project_id"])
        tasks = api.tasks(config["project_id"])

    day_type, source = resolve_day_type(tasks, today, config)
    actions, notes, section_names = plan(tasks, sections, day_type, today)

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"[{mode}] {today:%a %d %b %Y}: day type {day_type.upper()} "
          f"from {source}")
    print(f"{len(tasks)} tasks, {len(sections)} sections")
    for a in actions:
        title = a.task["content"]
        if len(title) > 50:
            title = title[:47] + "..."
        if a.kind == "move":
            current = section_names.get(a.task.get("section_id"), "(no section)")
            print(f"  move    {title!r}: {current} -> {a.section}  [{a.reason}]")
            if not dry_run:
                api.move(a.task["id"], next(s["id"] for s in sections
                                            if s["name"] == a.section))
        else:
            print(f"  delete  {title!r}  [{a.reason}]")
            if not dry_run:
                api.delete(a.task["id"])
    for n in notes:
        print(f"  note    {n}")
    verb = "planned" if dry_run else "done"
    print(f"{len(actions)} change(s) {verb}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

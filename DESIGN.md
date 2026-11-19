# Day-Type Routine Sorter: design

Concept page (interactive): https://claude.ai/artifact/TMuhGtZn9eikFDsGfQEQpo

## Problem
A Todoist section is one fixed value per task. Paul's routine tasks belong in
different sections depending on the type of day: office, work from home (WFH)
or non-working. Todoist has no way to express that.

## Solution in one line
Keep Todoist as the app. Each routine task carries its three slots in its
description, and a small scheduled script moves every card into the right
section for today's day type.

## Scope (v1)
- Todoist project **Routine** only (`6gm33Rmg3w725pq3`). Other projects later.
- Sections used: Morning, Afternoon, Evening, Wind down, Anytime, plus a new
  **Not today** section (last on the board) for tasks that don't apply today.
- Tasks with no slot line are never touched (e.g. `1000>1` in Habits, Weekly
  review, Someday review). Habits tasks that have a slot line (Read, YNAB,
  Daily Processing) *are* sorted out of Habits each day (Paul, Session 2).
- Subtasks are never moved on their own; they follow their parent.
- The script only changes a task's section, and deletes past override tasks.
  It never edits content, due dates, recurrence or completion. One
  exception: the **status card** (below), a task the script creates and
  owns.

## Status card
One uncompletable task (title starts `* `, so no checkbox) with no section,
so it sits in the board's first column, e.g.
`🏠 WFH day · Thu 19 Nov (weekly pattern)` or `… (override)`. Found by the
marker "Managed by the day-type sorter" in its description. Created if
missing, retitled when the day changes, never moved. If it is deleted, the
next run makes a new one.

## 1. Slot line (stored on each task)
One line anywhere in the task description:

```
office: evening | wfh: afternoon | off: morning
```

- Day-type keys: `office`, `wfh`, `off` (emoji 🏢 🏠 🌴 also accepted).
- Slot values: `morning`, `afternoon`, `evening`, `wind down`, `anytime`,
  or `skip` → goes to **Not today**.
- Case-insensitive. `·` also works as a separator; `wind-down` and
  `winddown` mean `wind down`. A day type missing from the line → task left
  where it is. An unknown slot value is reported and ignored.
- Convention: put the slot line last in the description, after a blank line.

## 2. Working out today's day type
Precedence, highest first:

1. **Override task**: a task in Routine titled `Day: office`, `Day: wfh` or
   `Day: off`, due on the date it applies to. Can be created days ahead from
   the iPhone (e.g. a bank holiday). The script parks it in Not today and
   deletes override tasks whose date has passed.
2. **Calendar**: *later, not in v1.* An all-day Outlook event named
   Office / WFH / Off, read from the calendar's published ICS link (kept as
   the GitHub secret `CALENDAR_ICS_URL`). Plan: about 40 extra lines; one-off
   all-day events only; fall back to the weekly pattern if the link fails.
3. **Weekly pattern** from `config.json` (default).

Time zone: Europe/London.

## 3. Running it
- Language: Python 3, standard library only (no dependencies to maintain).
- GitHub Actions schedule: hourly from 04:00 to 10:00 UTC. That covers 05:00
  London time in both GMT and BST, and picks up an override added later in
  the morning. Also runnable by hand (`workflow_dispatch`).
- Idempotent: a task already in the right section is not moved, so repeated
  runs are harmless.
- `DRY_RUN=1` prints the planned moves without making them. Default until
  Paul has checked a few dry runs.
- Todoist API token stored as the GitHub secret `TODOIST_API_TOKEN`.
  Never committed.

## Open items
- [x] Weekly pattern: Mon office, Tue WFH, Wed office, Thu WFH, Fri office.
- [x] Slot guesses on the concept page accepted as the starting point.
- [x] Todoist API: unified v1, base `https://api.todoist.com/api/v1`,
      `Authorization: Bearer <token>`. Confirmed live in Session 2:
      `GET /sections?project_id=` and `GET /tasks?project_id=` (paginated
      `{results, next_cursor}`; fields `section_id`, `parent_id`, `due.date`,
      `added_at`). Not yet exercised: `POST /tasks/{id}/move`
      `{"section_id"}` and `DELETE /tasks/{id}`; first used at go-live.

## Later
- Calendar day-type source (see step 2 above).
- Other projects besides Routine.

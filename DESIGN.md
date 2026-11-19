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
- Tasks with no slot line are never touched (e.g. the Habits section).
- The script only changes a task's section. It never edits content, due dates,
  recurrence or completion.

## 1. Slot line (stored on each task)
One line anywhere in the task description:

```
office: evening | wfh: afternoon | off: morning
```

- Day-type keys: `office`, `wfh`, `off` (emoji 🏢 🏠 🌴 also accepted).
- Slot values: `morning`, `afternoon`, `evening`, `wind down`, `anytime`,
  or `skip` → goes to **Not today**.
- Case-insensitive. A day type missing from the line → task left where it is.

## 2. Working out today's day type
Precedence, highest first:

1. **Override task**: a task in Routine titled `Day: office`, `Day: wfh` or
   `Day: off`, due on the date it applies to. Can be created days ahead from
   the iPhone (e.g. a bank holiday). The script parks it in Not today and
   deletes override tasks whose date has passed.
2. **Calendar** (phase 2, later): an all-day event named Office / WFH / Off.
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
- [ ] Paul's default weekly pattern (which weekday is which type).
- [ ] Confirm or correct the slot for each Routine task (concept page has guesses).
- [ ] Verify current Todoist API endpoints for listing tasks and moving a task
      to another section before writing the client.

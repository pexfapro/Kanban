# Day-Type Routine Sorter - progress

Last updated: 19 Nov 2026

## Status
Green - Live. GitHub Actions sorts the Todoist Routine board every morning
(hourly 04:07-10:07 UTC = 04:07-10:07 London in winter, 05:07-11:07 in
summer). Now in a week of real use before tuning.

## Done
- 19 Nov 2026 (Session 3): went live.
  - First real run by hand: 8 moves for a WFH Thursday; a second run planned
    0 changes, so repeat runs are harmless.
  - Todoist returned a brief 502/503 on the first attempt (nothing changed).
    Added retries (5s, 15s, 45s) for server errors, rate limits and network
    drops; 22 offline tests pass.
  - Added `.github/workflows/sort.yml`: hourly 04:07-10:07 UTC, plus a manual
    "Run workflow" button with a dry-run tick box. Bumped to checkout@v5
    (v4's Node 20 is being retired).
  - Created `main` and made it the default branch; Paul added the
    `TODOIST_API_TOKEN` repo secret. First GitHub run: success, 0 changes.
  - Overrides need no Shortcut: Todoist Quick Add `Day: off #Routine fri`
    files the task correctly (tested with 25 Dec, then deleted).
  - Failure alerts: GitHub iPhone app, Workflow Runs + Failed Workflows
    Only. Tested with a deliberate failing run (#3, session branch, reverted);
    the push arrived.
  - Week-1 aids: Inbox task "Sorter notes" (comment on it when a card lands
    wrong); one-off scheduled review Thu 26 Nov 12:40 sends a report and
    the Session 4 prompt.
- Earlier (Sessions 1-2, 19 Nov 2026): design agreed (DESIGN.md); `sorter.py`
  built with offline tests; Not today section and slot lines set up in
  Todoist; live dry runs matched the concept table.

## Decisions (append only)
- 19 Nov 2026: Keep Todoist; a scheduled script sorts Routine by day type -
  because Todoist can't hold one section per day type.
- 19 Nov 2026: Day type = Todoist override task > weekly pattern; Outlook
  all-day event check deferred until after go-live.
- 19 Nov 2026: Runs on GitHub Actions in this repo; Routine project only.
- 19 Nov 2026: Read, YNAB and Daily Processing get slot lines and leave
  Habits each day; `1000>1` stays put.
- 19 Nov 2026: Create a `main` branch and make it the default - because
  scheduled workflows only run from the default branch, and the old default
  was Session 1's design-only branch.

## Next steps
1. Use it for a week. Note any card that lands in the wrong slot, and any
   morning the board wasn't sorted.
2. Session 4: tune slot lines from those notes; review the week's run
   history in GitHub Actions.
3. Later: Outlook all-day event check (DESIGN.md, step 2); other projects.

Next-session prompt:
> Start session 4 of the Kanban day-type sorter. Read PROGRESS.md and
> DESIGN.md on `main`. Review the last week of "Sort Routine board" runs in
> GitHub Actions, then help me tune slot lines from these notes: [paste notes].

## Open questions and blockers
- None.

## How to use it
- Override a day from the iPhone: Todoist Quick Add
  `Day: office|wfh|off #Routine <date>` (e.g. `Day: off #Routine 24 dec`).
- Run it now: GitHub → Actions → Sort Routine board → Run workflow.
- Change the weekly pattern: `config.json`. Change a task's slots: edit the
  slot line in its Todoist description (`office: … | wfh: … | off: …`).

## Key files
- `DESIGN.md` - rules: slot lines, day-type precedence, scope.
- `sorter.py` / `test_sorter.py` - the sorter and its offline tests.
- `config.json` - time zone, Routine project id, weekly pattern.
- `.github/workflows/sort.yml` - the schedule.
- Concept page: https://claude.ai/artifact/TMuhGtZn9eikFDsGfQEQpo

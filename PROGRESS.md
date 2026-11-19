# Progress / handover

## Session 1 (19 Nov 2026): design, done
- Agreed approach: keep Todoist; a scheduled script sorts the Routine board by
  day type. See DESIGN.md.
- Decisions made by Paul:
  1. Day type: Todoist override task > weekly pattern. All-day Outlook
     event check deferred until after go-live.
  2. Runs on GitHub Actions in this repo.
  3. Routine project only for now.

## Session 2 (19 Nov 2026): sorter built, dry run only, done
Branch `claude/zen-knuth-tcge3i` (continues the Session 1 branch).
- `sorter.py` (stdlib only) + `test_sorter.py` (17 offline tests,
  `python3 -m unittest -v`) + `fixtures/routine_sample.json`.
  Try it offline: `python3 sorter.py --fixture fixtures/routine_sample.json --date 2026-11-21`.
- Todoist token saved as a network secret on the **Kanban** cloud
  environment (proxy injects it for api.todoist.com). Run live dry runs here
  with `DRY_RUN=1 TODOIST_API_TOKEN=proxy-injected python3 sorter.py`.
  This does NOT cover GitHub Actions; that needs its own repo secret.
- In Todoist: created **Not today** (last section); added slot lines to the 9
  Routine tasks from the concept-page table (appended after existing notes).
- Paul's decision: Read, YNAB and Daily Processing get slot lines and leave
  Habits each day; `1000>1` stays put.
- Live dry runs matched the table: Thu wfh 8 moves, Fri office 8, Sat off 9.
  A test `Day: off` task switched today to OFF and was planned for deletion
  the next day (test task then deleted).
- Nothing has been moved in Todoist yet.

## Next: Session 3, go live
1. First real run by hand in a cloud session: `DRY_RUN=0 TODOIST_API_TOKEN=proxy-injected
   python3 sorter.py`, then check the board. This is the first use of the
   move and delete endpoints; run it again to confirm it plans 0 changes.
2. Add the `TODOIST_API_TOKEN` repo secret (GitHub Settings → Secrets → Actions).
3. Add `.github/workflows/sort.yml`: hourly 04:00–10:00 UTC + workflow_dispatch,
   `DRY_RUN=0`. Scheduled workflows only run from the default branch, so
   merge this branch there first.
4. iPhone Shortcut or Todoist template for creating a `Day: …` override task.

## Session 4, tune after a week of use

## Later
- Add the Outlook all-day event check (DESIGN.md, step 2).

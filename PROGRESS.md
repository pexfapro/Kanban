# Progress / handover

## Session 1 (19 Nov 2026): design, done
- Agreed approach: keep Todoist; a scheduled script sorts the Routine board by
  day type. See DESIGN.md.
- Decisions made by Paul:
  1. Day type: weekly pattern with override first; all-day calendar event later.
  2. Runs on GitHub Actions in this repo.
  3. Routine project only for now.

## Next: Session 2, build the sorter (dry run only)
1. Fill in the weekly pattern in config.json (Paul to supply).
2. Write `sorter.py`: parse slot lines, resolve day type, plan moves, print them.
3. Get a Todoist API token into the session (request_credential for
   api.todoist.com) and run a dry run against the real Routine project.
4. Create the **Not today** section and add slot lines to the Routine tasks.

## Session 3, go live
- Add the `TODOIST_API_TOKEN` repo secret, add the workflow, switch off dry run.
- iPhone Shortcut or Todoist template for creating a `Day: …` override task.

## Session 4, tune after a week of use

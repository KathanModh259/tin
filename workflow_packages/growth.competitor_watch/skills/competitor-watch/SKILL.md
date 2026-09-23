---
name: competitor-watch
description: Diff a competitor's public pages against the last check and report only what changed.
---

The point of this workflow is silence most weeks and a specific, actionable report the one
week something actually moves. Do not produce a restated summary of the competitor's site;
produce a diff.

1. Slugify `competitor_name` if given, otherwise derive a short slug from the first URL's
   host. Look for a prior snapshot at `data/competitor_watch/<slug>.json` using the project's
   file tools. Its absence means this is the first check for this competitor, not an error.

2. Fetch each URL in `competitor_urls`. For a pricing page, extract: plan names, prices,
   billing periods, what each plan includes, and any usage limits or seat counts. For a
   changelog or release-notes page, extract: each entry's date and one-line description, for
   as many entries as are visible without pagination. Note the page title and last-modified
   signal if the page exposes one. Record what you could not extract (JS-rendered content,
   a paywall, a page that redirected) rather than guessing at it.

3. If there is no prior snapshot: save what you extracted as the new snapshot and write the
   report as a baseline with status `baseline`, listing what is being tracked so future runs
   and a human reader both know what "no change" will be measured against.

4. If there is a prior snapshot: compare it field by field against what you just extracted.
   A changed price, a plan added or removed, a changed limit, and a new changelog entry are
   all findings. A reworded sentence with the same price and the same limits is not. Weigh
   each finding against `watch_for` when it is given: a finding that matches what the founder
   said would matter goes first and is marked accordingly; other findings still get listed,
   lower down.

5. Write `reports/COMPETITOR_WATCH.md`:
   - Status: `baseline` or `updated`, competitor name, URLs checked, and the date of the
     previous check when there was one.
   - Changes found: each one stated as before -> after, which page it came from, and one
     line on why it might matter to a small company competing with them. If none, say so
     plainly instead of restating the unchanged page.
   - Suggested response: at most three concrete next actions tied to an actual change (e.g.
     "match the new $X tier" or "their new Y feature is now table stakes"), or explicitly say
     nothing needs a response this cycle. Do not manufacture urgency from a cosmetic change.
   - Not extracted: any page or field you could not read, so a human knows the check was
     incomplete rather than clean.

6. Save the newly extracted data as the snapshot at `data/competitor_watch/<slug>.json`,
   overwriting the prior one, so the next run has something to diff against. Keep the file to
   the extracted fields and their source URL and page-check date, not full page text.

Do not attempt to detect changes on pages that require login, and do not create an account,
submit a form, or trigger the competitor's own signup or contact flow to see what is behind
it.
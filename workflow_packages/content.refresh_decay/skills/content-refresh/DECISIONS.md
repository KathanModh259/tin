# One verdict per page, by first match

Walk the rules in order. The first rule whose condition holds is the verdict. Do not keep
looking for a better story, and do not give a page two verdicts. Record which rule fired and the
figures that satisfied it, so a reader can disagree with the rule rather than guess the reasoning.

A verdict is a recommendation. This run never acts on one.

## The thresholds

These are the numbers the rules below compare against. They are deliberately in one place so an
operator can argue with them without rereading the method.

| threshold | value | what goes wrong if it is set wrong |
| --- | --- | --- |
| `min_impressions` | 50 | Impressions in the current window, below which nothing else is decided. Lower, and verdicts are issued on noise: a page going two clicks to one is not a trend. Higher, and a small site's long tail is silenced as `insufficient evidence` forever, which is most of its traffic. |
| `clicks_drop` | 0.35 | The fall in clicks, window over window, that counts as a fall. Lower, and ordinary week-to-week variance reads as decay and the report cries wolf every run. Higher, and a page quietly bleeding a third of its traffic is never reported. |
| `position_worsening` | 1.5 | The worsening in impression-weighted average position that separates rule 5 from rule 6. Lower, and noise in a weighted average at low volume sends people to rewrite pages that never lost their ranking. Higher, and real ranking losses are misfiled as "the result page changed", which recommends no work at all. |
| `share_floor` | 0.25 | The share of a query's impressions a page needs before it counts as competing with a sibling. Lower, and every incidental co-appearance looks like self-competition — two pages showing for one query is ordinary. Higher, and genuine splits, where two pages each take a third, are missed. |
| `overlap_queries` | 3 | How many shared queries two pages need before they are called self-competing. At one, a single coincidence triggers a consolidation recommendation, and consolidation is not reversible for search traffic. Much higher, and only total duplicates are ever caught. |
| `rising` | 0.25 | The rise in clicks that counts as a rise. Only decides whether a working page is named as working, so the cost of being wrong is low in both directions. |

These are tuned for the site this workflow is for: a small company with tens of pages, not
thousands, where the long tail is the traffic. They are compared against windows as short as
fourteen days, so they are deliberately slow to call decay. `position_worsening` is the one to
argue with first — at 1.5 a page has to fall roughly from position six to position seven and a
half before anyone is asked to rewrite it, which errs toward not sending people to rewrite
things. Rule 6 exists for the same reason. An operator who would rather catch decay earlier
should lower it to 1.0 and expect more rewriting, some of it wasted.

## The rules

1. **Excluded.** The page is under an `exclude_paths` prefix. It is not reported.

2. **Too young to judge.** The page's first observed data, or a publication date given in
   `page_notes`, is less than `maturation_days` before the window end.
   → **leave alone (too young)**. Say when it becomes judgeable.

3. **Insufficient evidence.** Current-window impressions are below `min_impressions`, or the page
   appears only in a response marked censored, or the two windows are not comparable for it.
   → **insufficient evidence**. Name which of the three applies. This rule fires before every
   rule below it, so a quiet page is never called decayed and never called retired.

4. **Self-competing.** Two or more pages on this property share at least `overlap_queries`
   queries in the current window, each holding at least `share_floor` of that query's impressions.
   → **consolidate**. Name the keeper and the pages folded into it. The keeper is the page with
   the better impression-weighted position on the shared queries; break a tie with clicks, then
   with the page that is closer to the query's intent. Show the shared queries and each page's
   share. If a date-level response is available, say whether the pages alternate across days,
   which is stronger evidence than a single-window split.
   Two pages appearing for one query is ordinary. Both holding real share of it is not.

5. **Decayed.** Clicks fell by at least `clicks_drop`, and impression-weighted position worsened
   by at least `position_worsening`.
   → **refresh**. The page lost the ranking it had. Name the queries that fell hardest and what
   they were worth. This is the only verdict that asks anyone to rewrite anything.

6. **Slipped without losing rank.** Clicks fell by at least `clicks_drop`, but position held
   within `position_worsening`, or impressions fell while position improved.
   → **investigate the result page, not the page**. The ranking survived and the click did not:
   an AI overview, a new result feature, a changed intent, or fewer people searching at all.
   Say which of those the data can and cannot distinguish. Rewriting the page will not fix this,
   and this rule exists so that nobody is told to.

7. **Rising.** Clicks rose by at least `rising`.
   → **leave alone (working)**. Name the queries carrying the rise. A page that is working is a
   candidate to build on, not to edit.

8. **Never landed.** The page is older than `maturation_days`, has impressions above
   `min_impressions`, and has effectively no clicks in either window.
   → **retarget**. It is being shown and not chosen: the query it earns is not the query it
   answers, or the title does not match what was searched. Name the queries it appears for.

9. **Otherwise.** → **leave alone (stable)**.

## What no rule may do

No rule may recommend deleting a page. Retirement is a decision about a business, and the data
here cannot see links, conversions, revenue, or why the page was written. The strongest verdict
available is `retarget`.

No rule may fire on a fall explained by something in `seasonality_notes`. When an operator has
already named the cause, say so and move the page to `leave alone (explained)`.

No rule may use a figure from a censored response as if it were complete.

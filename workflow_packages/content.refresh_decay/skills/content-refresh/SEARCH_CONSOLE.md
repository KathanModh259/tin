# The Search Console contract, and what its numbers cannot say

Every request goes through the declared `search` service. Nothing else reaches the provider.

## The request shape

`sites.list` takes no arguments and confirms which property the project selected. Tin binds the
property; the run never chooses or changes it. If the selected property is missing, stop and
write a diagnostic report. A property covering a different host than the pages under discussion
is a mismatch to disclose, not a detail to smooth over.

`search_analytics.read` accepts exactly four arguments and no others:

| argument | bound |
| --- | --- |
| `start_date` | `YYYY-MM-DD` |
| `end_date` | `YYYY-MM-DD`, inclusive, at most 366 days after `start_date` |
| `dimensions` | 1–3 of `date`, `query`, `page`, `country`, `device`, `searchAppearance` |
| `row_limit` | 1–25000 |

There is no page filter, no query filter, no country filter and no row offset. Every request is
site-wide. Asking about one page is not possible; the page appears, or it does not come back.

A row is `{"keys": [...], "clicks": n, "impressions": n, "ctr": f, "position": f}`, with `keys`
in the order the dimensions were requested.

## The two limits that censor the answer

**`row_limit` truncates by clicks.** Rows come back ranked by clicks, descending. A page absent
from the response is a page that did not make the cut. It is not a page with no traffic.

**The 64000-byte response cap truncates again, and earlier.** A three-dimension row costs roughly
150–250 bytes, so a response holds a few hundred rows whatever `row_limit` says. Plan for 250–400
rows per request and treat the cap as the real bound.

Apply this test to every response, before reading a single number:

- Returned row count equals the requested `row_limit`, or the response reached the byte cap:
  **the result is censored**. Record the coverage as partial and name it in the report.
- Returned row count is below both: the result is complete **for the dimensions requested**.

A complete `page` response establishes which pages had clicks. It never establishes that a page
had none: zero-click pages with impressions rank below every page with one click.

**Never infer absence from a censored response.** Never infer absence from a failed request.
A page missing from a censored response gets `insufficient evidence`, not `retire`.

## What each figure means, and the mistakes that follow

**`position` is an impression-weighted average, not a rank.** A page at position 4.0 was probably
never shown at position 4. To combine positions across rows, weight by impressions:
`sum(position * impressions) / sum(impressions)`. Averaging averages is wrong and will invent
movement that did not happen.

**`ctr` is `clicks / impressions` for the returned rows only.** Recomputing it over a filtered
subset gives a different and usually more honest number. Say which one is shown.

**Query rows do not sum to page totals.** Search Console omits rare queries to protect anonymity.
The gap between the sum of a page's query rows and its page total is the anonymized remainder.
Report it as unknown coverage. Do not treat the shortfall as an error, and do not close it.

**The last two to three days are incomplete.** Data arrives late. End every window at least three
days before today, and say in the report which date it ended on. A window that includes yesterday
will always look like decay.

**Windows must be the same length and the same weekday shape.** Compare 28 days with the previous
28 days, never 28 with 30, and never a window containing five Mondays with one containing four.
Using multiples of seven days is the simplest way to hold this.

**A `page` key is a URL, not an article.** A redirect, a trailing-slash change, a parameter or a
protocol change makes the same article appear as two keys and look like two decayed pages. When
two keys differ only by scheme, host prefix, trailing slash, case or a tracking parameter, treat
them as one page and say that you merged them.

**Country and device are not filtered out.** A fall driven by one country or one device is a
composition change, not page decay.

## Cost and repetition

At most eight service calls for the whole run, counting `sites.list`. A censored response is not
grounds to fire the same request again with a larger limit; the byte cap will censor it again.
Spend a reserve call on a narrower date range only when that materially changes a verdict.
Provider data may be cached; cached is not newly collected.

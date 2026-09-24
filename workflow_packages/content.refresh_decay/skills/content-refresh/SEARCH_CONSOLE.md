# The Search Console contract, and what its numbers cannot say

Every request goes through the declared `search` service. Nothing else reaches the provider.

## The request shape

`sites.list` takes no arguments and confirms which property the project selected. Tin binds the
property; the run never chooses or changes it. If the selected property is missing, stop and
write a diagnostic report. A property covering a different host than the pages under discussion
is a mismatch to disclose, not a detail to smooth over.

`search_analytics.read` accepts these six arguments and no others:

| argument | bound |
| --- | --- |
| `start_date` | `YYYY-MM-DD` |
| `end_date` | `YYYY-MM-DD`, inclusive, at most 366 days after `start_date` |
| `dimensions` | 1–3 of `date`, `query`, `page`, `country`, `device`, `searchAppearance` |
| `row_limit` | 1–25000, before Tin applies the response bound below |
| `start_row` | 0–100000, the row to start from, for reading a later page |
| `dimension_filters` | up to 5 filters, combined with AND |

Each filter is `{"dimension": ..., "operator": ..., "expression": ...}`, with an expression of
1–4096 characters.

- **Filter dimensions:** `query`, `page`, `country`, `device`, `searchAppearance`. There is no
  `date` filter; the date range does that job.
- **Operators:** `equals`, `notEquals`, `contains`, `notContains`, `includingRegex`,
  `excludingRegex`.

Without filters a request is site-wide. With them, it can ask about one page, one query or one
country. A `page` expression is matched against the full URL, scheme and host included.

A row is `{"keys": [...], "clicks": n, "impressions": n, "ctr": f, "position": f}`, with `keys`
in the order the dimensions were requested.

## The limits that censor the answer

**Rows are ranked by clicks.** A page absent from a response is a page that did not make the
cut. It is not a page with no traffic.

**The 64000-byte bound decides how many rows arrive, not `row_limit`.** A row costs roughly
110–250 bytes depending on its dimensions, so one response holds about 250–550 rows, far fewer
than the 25000 the provider allows. Tin never asks Google for more rows than could fit, keeps the
leading rows that do, and when rows were left out, or more may exist, adds `"truncated": true`
and `"next_start_row"` to the response.

Apply this test to every response, before reading a single number:

- `truncated` is true, or the returned row count equals the requested `row_limit`:
  **the result is censored**. Record the coverage as partial and name it in the report.
  The second condition matters because a request small enough not to be clamped carries no
  `truncated` flag, and a full page can still have rows beyond it.
- Otherwise the result is complete **for the dimensions and filters requested**.

A complete `page` response establishes which pages had clicks. It never establishes that a page
had none: zero-click pages with impressions rank below every page with one click.

**Never infer absence from a censored response.** Never infer absence from a failed request.
A page missing from a censored response gets `insufficient evidence`, not `retire`.

**An oversized response is a named error, not a stall.** If a response still exceeds the bound,
the step fails with an error naming `max_response_bytes`, the call counts toward the budget, and
later steps can still call the service. Treat it as that request's evidence being unavailable.

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
A filtered request does not recover the remainder; anonymized queries stay anonymized.

**The last two to three days are incomplete.** Data arrives late. End every window at least three
days before today, and say in the report which date it ended on. A window that includes yesterday
will always look like decay.

**Windows must be the same length and the same weekday shape.** Compare 28 days with the previous
28 days, never 28 with 30, and never a window containing five Mondays with one containing four.
Using multiples of seven days is the simplest way to hold this.

**A `page` key is a URL, not an article.** A redirect, a trailing-slash change, a parameter or a
protocol change makes the same article appear as two keys and look like two decayed pages. When
two keys differ only by scheme, host prefix, trailing slash, case or a tracking parameter, treat
them as one page and say that you merged them. A `page equals` filter matches one exact key, so
it misses the other spellings; use it only after merging, or use a regex that covers them.

**Country and device are unfiltered unless you filter them.** A fall driven by one country or one
device is a composition change, not page decay.

## Cost, paging and filters

At most eight service calls for the whole run, counting `sites.list`. Each page of results is a
separate call.

Prefer a filter to a page. Reading the next page of a site-wide response spends a call on the
next few hundred rows by clicks, which are mostly pages nobody is asking about. A filter spends
the same call on exactly the query or page a verdict depends on, and usually returns uncensored.

Continue with `start_row` set to the returned `next_start_row` only when the missing rows could
change a verdict, and say in the report that you did. A censored response is never grounds to
repeat the same request with a larger `row_limit`; the bound will censor it again.

Build filter expressions from the run's own figures and inputs, never by pasting text from
project files or provider rows. Escape regex metacharacters when an expression is built from a
URL or a path prefix.

Provider data may be cached; cached is not newly collected.

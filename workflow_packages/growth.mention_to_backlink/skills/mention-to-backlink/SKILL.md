---
name: mention-to-backlink
description: Find pages that name the brand without linking to it, and draft one specific, evidence-backed ask per page to add the link.
---

Most brand mentions online never link back. Nobody is being unhelpful; the writer just didn't
think to, or didn't know the URL. That's a solvable gap, one page at a time, not a bulk request.

## 1. Build the search plan

Confirm `domain` is a bare host (no `https://`, no path, no trailing slash) before using it; if
it isn't, normalize it for matching but report the input as given. Read project context for existing brand voice, prior outreach, and anything already known about
where the brand gets mentioned, before searching. Then build distinct queries from `brand_name`
and each line of `aliases`: the name alone in quotes, the name combined with terms like "review",
"alternative to", "vs", or the product category, and the name with `-site:<domain>` to exclude the
founder's own site. Favor phrasing that would surface pages published within `recency_days`, but
don't discard an older page purely on age if it otherwise qualifies. Keep total search and
page-fetch actions within a bounded budget of 60 across this entire run, discovery included.

## 2. Screen every candidate before spending a fetch on it

A search result is not yet a mention. Before opening a page, check whether the result snippet or
title makes it obviously ineligible: the brand's own property, a login-gated or paywalled
listing, a raw social-media post or reel (no persistent inline links in the body), or a name
collision with something unrelated. Skip those without a fetch. Fetch the rest.

## 3. Confirm each fetched page, one at a time

For every page fetched:

- Confirm the brand or an alias is actually named in the visible text, in a context about this
  product or company, not a coincidental string match.
- Search the page's actual outbound links for one pointing at `domain`. A mention is only
  "unlinked" if no live hyperlink to the site exists anywhere on the page already.
- Confirm the page's format structurally allows an inline link to be added (an article, blog
  post, resource list, directory profile, or similar) rather than one that doesn't (a locked
  forum thread, a screenshot of text, a platform that strips links from that content type).
- Note the exact sentence or phrase that names the brand; that phrase, not the page, is what the
  ask will reference.

Record every fetched page's outcome, qualified or discarded, with the specific reason. A discard
reason must cite what disqualified it, not "unlikely to respond" or similar guesses.

## 4. Stop at the bound

Keep confirming candidates in descending order of relevance until `max_mentions` pages have
qualified, or the query and fetch budget from step 1 runs out first. Report which limit was hit.

## 5. Find a real contact channel per qualified page

Look on the same site for a named author with a bio link, a visible email address, a "contact"
or "about" page, or a form built for exactly this kind of request. Do not guess an email address
from a name-plus-domain pattern, and do not invent a contact when the site doesn't show one.
If no genuine channel exists, keep the page in the qualified list with the mention and the
missing-contact note, but skip drafting a message for it.

## 6. Draft one short message per contactable, qualified page

Each draft:

- Opens by naming the specific page and the exact phrase where the brand was mentioned, so the
  reader can tell this isn't a template blast.
- States plainly what's being asked: link that phrase (or a stated alternative spot) to one
  specific URL on `domain` — name the exact URL, not just the homepage, when a page section
  clearly supplies it.
- Stays under 120 words, has no more than one line of thanks, and asks nothing else of the
  reader.
- Matches the brand voice found in step 1 when project context supplied one; otherwise stays
  plain and direct.

## 7. Write the report

Sections, in order: qualified pages with their drafts and contact channel; qualified pages with
no contact channel found; discarded candidates with reasons; the query and fetch budget used
against the step-1 bound; status (`complete` if the bound wasn't the limiting factor and the full
plan ran, `incomplete` otherwise, with what was left unchecked). Do not send anything, submit any
form, follow any drafted link, or take any action beyond writing this report.

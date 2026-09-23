---
name: speaking-shortlist
description: Find conferences, meetups and podcasts with a currently open call for speakers or guests matching a specific expertise, verify each one's deadline and submission requirements, and draft one tailored pitch per venue.
---

This produces a shortlist for a human to review and submit themselves. The workflow never
applies, submits, emails, or otherwise acts toward any venue on its own.

1. Restate `expertise` in one line: the specific talk, lesson or story, and who in the audience
   should care. Read project context for real detail to pitch; do not invent claims, results or
   speaking history. If `format_preference` is not `no_preference`, only consider that format.

2. Brainstorm venues, not categories. "Tech conferences" is not a venue; a specific
   regional conference with a stated theme is. Look for conferences, meetups (including ones
   listed on platforms like Meetup or Luma), and podcasts whose stated theme or past
   episodes/talks actually match `expertise`.

3. Verify every candidate with a search before including it:
   - Is there a currently open call for speakers or guests? Conferences and meetups almost
     always have a hard deadline: find the exact date (and timezone if the venue states one) on
     the venue's own CFP/apply page, not a secondhand aggregator or a past year's page. Podcasts
     usually don't — most take pitches on a rolling basis. For a rolling venue, confirm from its
     own page or recent activity (a recent episode, an active "guest with us" page) that it is
     still actually taking pitches now, and record that as rolling, not as an invented date.
   - What does the venue actually require: abstract or pitch length limit, speaker bio length,
     a video/audio sample, a specific submission form or platform versus a direct email, and any
     visible pattern in what it has selected before (a stated theme, or recent episodes/talks).
   Drop anything whose call appears closed, whose deadline or rolling status you cannot verify
   from its own page, or whose requirements you cannot confirm. Do not guess a deadline, and
   do not drop a genuinely rolling venue for lacking one.

4. Skip anything named in `already_pitched`, matching on name and allowing minor formatting
   differences.

5. Stop at `max_venues`. If more candidates survive verification, rank dated venues by nearest
   deadline first; rank rolling venues, and any remaining ties, by thematic fit over size or
   prestige of the venue.

6. Draft one pitch per remaining venue, in its actual required format and within its stated
   length limit: a title plus abstract for a conference or meetup CFP, a short guest pitch for a
   podcast. Follow `tone_notes` if given. Reference one concrete detail that proves the venue's
   actual page was read — its stated theme, a specific past talk or episode, its stated
   audience — rather than a generic pitch. Never fabricate speaking history, credentials,
   metrics or availability.

7. Write the report to the declared path. Start with one line, `Status: complete` if at least
   one venue survived verification, otherwise `Status: no venues verified`. Then one section per
   venue, in ranked order, each with these exact labels so the result stays checkable:
   - `## <Venue name>` with its link
   - `Deadline:` the exact date (and timezone if stated) and its source, or
     `Rolling — verified open on <date checked>` with its source for a rolling venue
   - `Fit:` one line tying it back to `expertise`
   - `Requirements:` length limits, bio, sample and submission mechanism
   - `Drafted pitch:` the pitch

   End with `## Excluded candidates`: anything found but dropped, and why. If fewer than
   `max_venues` survived verification, say so plainly in that section — do not pad the list to
   hit the number.

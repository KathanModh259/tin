---
name: pricing-watch
description: Inspect competitor pricing and packaging, detect changes against historical runs, and write an actionable commercial watchdog report.
---

# Competitor Pricing & Packaging Watchdog

Inspect a competitor's pricing page, extract structured packaging data, compare with previous project snapshots, and produce a decision-oriented commercial brief.

## Phase 1: Locate & Ingest Pricing Page
1. Check the supplied `competitor_url`. If it is a homepage or general product URL, locate the public pricing link (`/pricing`, `/plans`, `/pricing-and-packaging`).
2. Read the page content. Extract:
   - Currency and billing frequencies (monthly vs annual discounts).
   - Plan names in ascending order of price.
   - Prices per billing interval (per user/seat, usage tier, flat rate).
   - Usage caps & allowances (e.g. "Up to 5 team members", "10,000 events/mo").
   - Free tier or free trial specifics (card required vs cardless, trial length).
   - Gated capabilities (which major features appear exclusively on Pro vs Enterprise).
   - Primary Call-to-Action (CTA) label per plan (e.g. "Start free", "Book a demo").
   - Add-on fees or overage rates if publicly disclosed.
3. If public pricing is hidden behind a sales wall ("Contact Us" only), record this explicitly as an enterprise-only gating model.

## Phase 2: Historical Snapshot Discovery & Diffing
1. Scan project Files under `reports/pricing-watch/*.md`.
2. Look for existing reports that match `competitor_name` inside their metadata or JSON evidence fence.
3. If found, identify the most recent completed report. Extract its `tin-pricing-watch` JSON evidence block.
4. Execute a semantic diff against the current extraction:
   - **Price Delta**: Price increases, price drops, discount adjustments.
   - **Packaging Shifts**: Features moved up-tier (paywalled) or down-tier (democratized).
   - **Threshold Changes**: Seat minimums added/removed, quota limits altered.
   - **Trial/Free Shifts**: Free tier discontinued, trial duration shortened, credit card requirement changed.
   - **Positioning Pivot**: Hero headline or tier naming changes indicating a market pivot.
5. If no prior report exists for this competitor, classify this run as **Baseline Snapshot**.

## Phase 3: Action Matrix Generation
Based on the diff and optional `our_pricing_context`, determine concrete tactical responses:
- **Opportunity Plays**:
  - *Competitor raised prices or added seat minimums* -> Draft counter-positioning for sales outbound; update comparison page hero banner.
  - *Competitor moved a popular feature to Enterprise* -> Highlight that feature in your own Starter/Pro marketing.
- **Threat Mitigations**:
  - *Competitor lowered entry price or added free tier* -> Evaluate self-serve onboarding friction; reinforce unique value propositions.
- **Sales Battlecard Updates**:
  - Exact talking points for sales conversations when prospective buyers mention this competitor.

## Phase 4: Report Synthesis
Follow `REPORT.md` precisely. Ensure the report contains both the human-readable executive analysis and the machine-readable `tin-pricing-watch` JSON block at the bottom.

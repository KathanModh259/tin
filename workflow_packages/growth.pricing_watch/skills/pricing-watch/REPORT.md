# Report Template & Rendering Rules

The generated report at `reports/pricing-watch/{run_id}.md` must strictly follow this structure:

```markdown
# Pricing & Packaging Watchdog: [Competitor Name]
*Generated: [UTC Timestamp] | Source: [Competitor URL] | Run: [run_id]*

## 1. Executive Verdict & What Changed
- **State**: [Baseline Snapshot | Detected Changes | No Changes Detected]
- **Key Takeaway**: 1-3 bullet points summarizing the most critical movement (or confirming stability).

## 2. Action Matrix (What To Do Next)
| Trigger Detected | Impact Level | Recommended Immediate Action | Owner / Surface |
|---|---|---|---|
| [e.g. Added 5-seat minimum to Pro] | High Opportunity | [Update 'vs Competitor' landing page with 'No seat minimums' badge] | Marketing / Website |
| [e.g. Raised Starter plan from $19 to $29] | Medium Opportunity | [Arm sales team with pricing comparison battlecard] | Sales / Outbound |

## 3. Current Tier & Packaging Matrix
| Tier Name | Monthly Price | Annual (Mo. Eq.) | Unit / Minimum | Free Trial / CTA | Key Gated Features |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

## 4. Semantic Diff (vs Previous Snapshot)
*If baseline snapshot, note: "Initial baseline captured. Future runs will diff against this baseline."*
- **Pricing Deltas**: [Before vs After]
- **Packaging & Feature Gates**: [Additions / Removals]
- **CTA & Messaging**: [Hero tagline or button copy changes]

## 5. Competitive Implications for Your Business
*(Only populated when our_pricing_context was provided)*
- Observational analysis of how their structure compares to yours.
- Value gap and vulnerability assessment.

---

## Evidence
```json tin-pricing-watch
{
  ... normalized extraction conforming to SCHEMA.md ...
}
```
```

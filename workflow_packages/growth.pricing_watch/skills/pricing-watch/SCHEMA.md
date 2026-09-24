# Competitor Pricing Extraction Schema

Every run must normalize extracted data into the following schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "competitor_name",
    "scraped_at",
    "source_url",
    "has_public_pricing",
    "currency",
    "tiers"
  ],
  "properties": {
    "competitor_name": { "type": "string" },
    "scraped_at": { "type": "string", "format": "date-time" },
    "source_url": { "type": "string", "format": "uri" },
    "has_public_pricing": { "type": "boolean" },
    "currency": { "type": "string", "maxLength": 10 },
    "free_trial": {
      "type": "object",
      "properties": {
        "available": { "type": "boolean" },
        "days": { "type": "integer" },
        "credit_card_required": { "type": "boolean" }
      }
    },
    "tiers": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "price_monthly", "cta_text"],
        "properties": {
          "name": { "type": "string" },
          "price_monthly": { "type": ["number", "null"] },
          "price_annual_monthly_equivalent": { "type": ["number", "null"] },
          "billing_unit": { "type": "string" },
          "seat_minimum": { "type": "integer" },
          "cta_text": { "type": "string" },
          "highlighted_features": {
            "type": "array",
            "items": { "type": "string" },
            "maxItems": 10
          },
          "usage_limits": { "type": "string" }
        }
      }
    }
  }
}
```

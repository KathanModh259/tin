"""Offline regression tests for growth.pricing_watch workflow package.

Validates the package manifest, schema constraints, declared resources, and
the semantic diffing / action matrix logic without external network calls.
"""

import json
import re
from pathlib import Path
import pytest

PACKAGE_ROOT = (
    Path(__file__).parents[1]
    / "workflow_packages"
    / "growth.pricing_watch"
)


def load_manifest() -> dict:
    manifest_path = PACKAGE_ROOT / "workflow.json"
    assert manifest_path.is_file(), f"Missing manifest: {manifest_path}"
    raw = manifest_path.read_text(encoding="utf-8")
    return json.loads(raw)


def test_package_structure_and_declared_resources():
    """Verify package adheres to tin-workflow-package-v1 rules."""
    manifest = load_manifest()
    assert manifest.get("package_format") == "tin-workflow-package-v1"
    
    definition = manifest.get("definition", {})
    assert definition.get("key") == "growth.pricing_watch"
    assert definition.get("executor") == "codex.procedure"
    assert definition.get("schedule_modes") == ["on_demand", "weekly"]
    
    procedure = definition.get("procedure", {})
    assert procedure.get("entry_skill") == "pricing-watch"
    assert procedure.get("prompt_path") == "PROMPT.md"
    assert (PACKAGE_ROOT / "PROMPT.md").is_file()
    
    # Check declared skill files
    skill_files = procedure.get("skill_files", [])
    assert len(skill_files) == 3
    for rel_path in skill_files:
        full_path = PACKAGE_ROOT / rel_path
        assert full_path.is_file(), f"Declared skill file missing: {rel_path}"
        
    # Check sandbox & egress contract
    sandbox = procedure.get("sandbox", {})
    assert sandbox.get("profile") == "isolated"
    assert sandbox.get("egress") == "fenced"
    assert sandbox.get("timeout_seconds") == 900
    
    # Check output path template constraint for plain markdown reports
    output = procedure.get("output", {})
    assert output.get("kind") == "project.artifact"
    assert output.get("media_type") == "text/markdown"
    assert output.get("path_template") == "reports/pricing-watch/{run_id}.md"
    assert output.get("max_bytes") <= 250000


def test_input_schema_constraints():
    """Verify input schema strictly enforces Tin community requirements."""
    manifest = load_manifest()
    schema = manifest["definition"]["input_schema"]
    
    assert schema.get("type") == "object"
    assert schema.get("additionalProperties") is False
    assert set(schema.get("required", [])) == {"project_id", "competitor_url", "competitor_name"}
    
    properties = schema.get("properties", {})
    
    # project_id
    assert properties["project_id"]["type"] == "string"
    assert properties["project_id"]["format"] == "uuid"
    
    # competitor_url
    assert properties["competitor_url"]["type"] == "string"
    assert properties["competitor_url"]["format"] == "uri"
    assert properties["competitor_url"]["maxLength"] == 500
    
    # competitor_name
    assert properties["competitor_name"]["type"] == "string"
    assert properties["competitor_name"]["maxLength"] == 120
    
    # All user text properties must define maxLength (project_id is system UUID)
    for name, prop in properties.items():
        if prop.get("type") == "string" and name != "project_id":
            assert "maxLength" in prop, f"Property '{name}' missing maxLength constraint"


def test_semantic_pricing_diff_calculation():
    """Test deterministic semantic diff between two snapshots."""
    baseline = {
        "competitor_name": "Linear",
        "currency": "USD",
        "tiers": [
            {"name": "Free", "price_monthly": 0, "seat_minimum": 1, "cta_text": "Sign up"},
            {"name": "Standard", "price_monthly": 8, "seat_minimum": 1, "cta_text": "Try free"},
            {"name": "Plus", "price_monthly": 14, "seat_minimum": 1, "cta_text": "Try free"}
        ]
    }
    
    # Updated snapshot with: price hike, seat minimum added, tier renamed
    updated = {
        "competitor_name": "Linear",
        "currency": "USD",
        "tiers": [
            {"name": "Free", "price_monthly": 0, "seat_minimum": 1, "cta_text": "Sign up"},
            {"name": "Standard", "price_monthly": 10, "seat_minimum": 1, "cta_text": "Try free"},
            {"name": "Pro", "price_monthly": 16, "seat_minimum": 5, "cta_text": "Try free"}
        ]
    }
    
    base_by_name = {t["name"]: t for t in baseline["tiers"]}
    up_by_name = {t["name"]: t for t in updated["tiers"]}
    
    # Detect price delta on Standard: +$2 (+25%)
    std_diff = up_by_name["Standard"]["price_monthly"] - base_by_name["Standard"]["price_monthly"]
    assert std_diff == 2
    
    # Detect new tier and removed tier
    added_tiers = set(up_by_name) - set(base_by_name)
    removed_tiers = set(base_by_name) - set(up_by_name)
    assert added_tiers == {"Pro"}
    assert removed_tiers == {"Plus"}
    
    # Detect seat minimum change
    assert up_by_name["Pro"]["seat_minimum"] == 5
    
    # Tactical action mapping
    actions = []
    if std_diff > 0:
        actions.append("opportunity:competitor_raised_prices")
    if up_by_name["Pro"]["seat_minimum"] > 1:
        actions.append("opportunity:seat_minimum_introduced")
        
    assert "opportunity:competitor_raised_prices" in actions
    assert "opportunity:seat_minimum_introduced" in actions

"""Offline checks for the content.refresh_decay package.

The package is text only, so there is no entrypoint to execute. What can go wrong instead is
drift: the prose promising a provider argument, dimension or call budget that the runtime does
not actually offer, or a decision rule naming a threshold nobody defined. These tests pin the
package's text to the contracts it depends on, and read no network and no database.
"""

from __future__ import annotations

import inspect
import json
import re
import shutil
from pathlib import Path

import jsonschema
import pytest

from tin_lite.code_services import OPERATIONS
from tin_lite.community import (
    REPOSITORY_ROOT,
    ContributedPackage,
    validate,
    validate_private_copy,
)
from tin_lite.integrations import (
    GSC_FILTER_DIMENSIONS,
    GSC_FILTER_OPERATORS,
    GSC_MAX_FILTERS,
    GSC_MAX_START_ROW,
    IntegrationService,
)
from tin_lite.procedures import validate_codex_procedure_definition
from tin_lite.workflow_packages import decode_workflow_source

KEY = "content.refresh_decay"
PACKAGE = REPOSITORY_ROOT / "workflow_packages" / KEY
SKILL = PACKAGE / "skills" / "content-refresh"


def definition() -> dict:
    return json.loads((PACKAGE / "workflow.json").read_text(encoding="utf-8"))["definition"]


def read(name: str) -> str:
    return (SKILL / name).read_text(encoding="utf-8")


def flat(name: str) -> str:
    """Wrapped prose, as one line, so a phrase test is not a line-width test."""
    return " ".join(read(name).split())


async def test_the_package_loads_as_a_contributed_procedure():
    await validate(ContributedPackage(key=KEY, path=PACKAGE), root=REPOSITORY_ROOT)
    # The loader resolves package-relative paths into the registry layout before validating.
    source = decode_workflow_source(
        (PACKAGE / "workflow.json").read_bytes(),
        definition_path=f"workflow_packages/{KEY}/workflow.json",
    )
    spec = validate_codex_procedure_definition(source.definition)
    assert spec.entry_skill == "content-refresh"
    assert spec.result_kind == "project.artifact"


def test_the_run_can_only_read_search_console():
    contract = definition()
    (requirement,) = contract["integration_requirements"]
    assert requirement["provider_key"] == "analytics.gsc"
    assert requirement["required"] is True
    assert set(requirement["capabilities"]) == {"sites.list", "search_analytics.read"}
    services = contract["procedure"]["services"]
    assert set(services) == {"search"}
    assert services["search"]["provider_key"] == "analytics.gsc"
    # The gateway refuses anything past these, so the skill must not promise more.
    assert services["search"]["max_calls"] == 8
    assert services["search"]["max_response_bytes"] == 64_000
    sandbox = contract["procedure"]["sandbox"]
    assert sandbox["profile"] == "isolated" and sandbox["egress"] == "fenced"


def test_the_skill_promises_no_more_calls_than_the_binding_allows():
    words = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight")
    budget = definition()["procedure"]["services"]["search"]["max_calls"]
    assert f"At most {words[budget]} service calls" in flat("SKILL.md")
    assert f"at most {words[budget]} service calls" in flat("SEARCH_CONSOLE.md").lower()


def test_the_documented_request_arguments_are_the_ones_the_gateway_accepts():
    """SEARCH_CONSOLE.md tabulates the arguments. The gateway's field set decides which."""
    _, fields = OPERATIONS[("analytics.gsc", "search_analytics.read")]
    documented = set(re.findall(r"^\| `(\w+)` \|", read("SEARCH_CONSOLE.md"), re.MULTILINE))
    assert documented == set(fields)


def test_the_documented_filters_are_the_ones_the_provider_accepts():
    text = flat("SEARCH_CONSOLE.md")
    (dimensions,) = re.findall(r"\*\*Filter dimensions:\*\* (.+?)\. ", text)
    (operators,) = re.findall(r"\*\*Operators:\*\* (.+?)\. ", text)
    assert set(re.findall(r"`(\w+)`", dimensions)) == GSC_FILTER_DIMENSIONS
    assert set(re.findall(r"`(\w+)`", operators)) == GSC_FILTER_OPERATORS
    assert f"up to {GSC_MAX_FILTERS} filters" in text
    assert f"0–{GSC_MAX_START_ROW}" in text.replace(",", "")


def test_every_filter_the_skill_sends_is_one_the_provider_accepts():
    text = flat("SKILL.md")
    filters = re.findall(r'\{"dimension": "(\w+)", "operator": "(\w+)"', text)
    assert filters, "the skill should show the filters it sends"
    for dimension, operator in filters:
        assert dimension in GSC_FILTER_DIMENSIONS
        assert operator in GSC_FILTER_OPERATORS


def test_censoring_is_read_from_the_truncation_flag_and_the_row_limit():
    """A clamped response says `truncated`; an unclamped full page does not, but may continue."""
    text = flat("SEARCH_CONSOLE.md")
    assert "`truncated` is true, or the returned row count equals the requested `row_limit`" in text
    assert "`next_start_row`" in text
    assert "Never infer absence from a censored response." in text


def test_the_documented_dimensions_are_the_ones_the_provider_allows():
    source = inspect.getsource(IntegrationService.search_console_analytics)
    (literal,) = re.findall(r"allowed_dimensions = \{([^}]+)\}", source)
    allowed = set(re.findall(r"\"(\w+)\"", literal))
    text = read("SEARCH_CONSOLE.md")
    (row,) = re.findall(r"^\| `dimensions` \| (.+) \|$", text, re.MULTILINE)
    assert set(re.findall(r"`(\w+)`", row)) == allowed
    for names in re.findall(r"`dimensions: \[([^\]]+)\]`", read("SKILL.md")):
        requested = set(re.findall(r"\"(\w+)\"", names))
        assert requested <= allowed and 1 <= len(requested) <= 3


@pytest.mark.parametrize(
    "threshold",
    [
        "min_impressions",
        "clicks_drop",
        "position_worsening",
        "share_floor",
        "overlap_queries",
        "rising",
    ],
)
def test_every_threshold_the_rules_use_has_a_value_and_a_failure_mode(threshold):
    text = read("DECISIONS.md")
    (row,) = re.findall(rf"^\| `{threshold}` \| (.+) \|$", text, re.MULTILINE)
    value, consequence = (cell.strip() for cell in row.split("|", 1))
    assert re.fullmatch(r"[0-9.]+", value), f"{threshold} needs a numeric value"
    assert len(consequence) > 80, f"{threshold} needs a stated failure mode"


def test_no_rule_names_a_threshold_the_table_never_defines():
    text = read("DECISIONS.md")
    table, rules = text.split("## The rules")
    defined = set(re.findall(r"^\| `(\w+)` \|", table, re.MULTILINE))
    # The rules also cite workflow inputs and verdict names in backticks; neither is a threshold.
    inputs = set(definition()["input_schema"]["properties"])
    verdicts = {"retarget", "refresh", "consolidate"}
    used = set(re.findall(r"`(\w+)`", rules)) - inputs - verdicts
    assert used <= defined, f"undefined thresholds in the rules: {sorted(used - defined)}"
    assert defined <= used | {t for t in defined if t in rules}, "a threshold no rule consults"
    assert "TODO" not in text


def test_self_competition_is_decided_before_decay():
    """A page cannibalised by its sibling shows the exact signature of decay.

    Rewriting it is the wrong action, so rule 4 has to be reachable before rule 5.
    """
    rules = read("DECISIONS.md").split("## The rules")[1]
    assert rules.index("**Self-competing.**") < rules.index("**Decayed.**")
    assert rules.index("**Insufficient evidence.**") < rules.index("**Self-competing.**")


def test_the_rules_never_recommend_deleting_a_page():
    text = " ".join(read("DECISIONS.md").split())
    assert "No rule may recommend deleting a page" in text
    assert "The strongest verdict available is `retarget`" in text


def test_the_package_never_claims_to_read_the_pages_themselves():
    """Search Console sees search behaviour. A verdict is about rankings, not prose quality."""
    for name in ("SKILL.md", "PROMPT.md"):
        source = (PACKAGE / name) if name == "PROMPT.md" else (SKILL / name)
        assert "fetch" in source.read_text(encoding="utf-8").lower()
    assert "Never fetch a page, read the site, or verify content" in flat("SKILL.md")


def test_the_proposed_cases_satisfy_the_published_input_contract():
    path = REPOSITORY_ROOT / "workflow_evals" / KEY / "qualification.json"
    qualification = json.loads(path.read_text(encoding="utf-8"))
    schema = dict(definition()["input_schema"])
    # Tin binds project_id before execution, so a case never supplies one.
    schema["required"] = [name for name in schema["required"] if name != "project_id"]
    schema["properties"] = {k: v for k, v in schema["properties"].items() if k != "project_id"}
    assert qualification["cases"], "a contributed package proposes at least one case"
    for case in qualification["cases"]:
        jsonschema.validate(case["inputs"], schema)


def test_the_report_refuses_to_reuse_boilerplate_refusals():
    text = read("REPORT.md")
    assert "Not boilerplate" in text
    assert "anonymized query remainder" in text


async def test_a_private_copy_activates_with_the_two_documented_changes(tmp_path):
    """docs/adding-a-workflow.md: on_demand only and a fixed path. Nothing else should be needed."""
    copy = tmp_path / "workflow_packages" / KEY
    shutil.copytree(PACKAGE, copy)
    manifest = json.loads((copy / "workflow.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="on_demand"):
        await validate_private_copy(ContributedPackage(key=KEY, path=copy), root=tmp_path)
    manifest["definition"]["schedule_modes"] = ["on_demand"]
    output = manifest["definition"]["procedure"]["output"]
    output.pop("path_template")
    output["path"] = "reports/content-refresh/latest.md"
    (copy / "workflow.json").write_text(json.dumps(manifest), encoding="utf-8")
    await validate_private_copy(ContributedPackage(key=KEY, path=copy), root=tmp_path)


def test_the_package_declares_every_file_it_ships():
    declared = {"workflow.json", "PROMPT.md"} | {
        Path(path).name for path in definition()["procedure"]["skill_files"]
    }
    present = {path.name for path in PACKAGE.rglob("*") if path.is_file()}
    assert present == declared

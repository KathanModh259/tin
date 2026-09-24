"""Reviewed ranking resource for organic.error_surface; no provider or model calls in CI."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "workflow_packages/organic.error_surface"
RESOURCES = PACKAGE / "skills/error-surface"


def resource(name):
    path = RESOURCES / name
    blocks = re.findall(r"```python\n(.*?)\n```", path.read_text(encoding="utf-8"), re.S)
    assert len(blocks) == 1
    namespace = {}
    # Only the fixed repository resource executes here, never extracted candidate text.
    exec(compile(blocks[0], str(path), "exec"), namespace)  # noqa: S102
    return namespace


@pytest.fixture
def ranking():
    return resource("RANKING.md")


def candidate(message, **overrides):
    return {
        "message": message,
        "surface": "api",
        "call_sites": 3,
        "coverage": "none",
        "evidence": "src/errors.py:12",
        **overrides,
    }


def test_an_error_code_lifts_a_message_above_equally_long_prose(ranking):
    found = ranking["searchability"]
    coded = found("ERR_CONN_REFUSED: upstream database rejected the connection pool handshake")
    prose = found("The upstream database rejected the connection pool handshake for this call")
    assert coded > prose > 0
    assert coded == 90


def test_specificity_past_five_words_still_earns_credit(ranking):
    found = ranking["searchability"]
    # A linear cap scored these equally. The longer one names four directories and the fix.
    detailed = found(
        "Could not find build output directory (out, dist, build, .next). Ensure your "
        'package.json has a "build" script that produces one of these directories.'
    )
    terse = found("Extraction produced no folders")
    assert detailed > terse > 0


def test_an_operator_message_is_near_worthless_on_a_hosted_product(ranking):
    scored = ranking["score_candidate"](
        candidate("UPSTASH_REDIS_URL is not set", surface="operator")
    )
    # The string is genuinely findable; it is the audience that makes it cheap.
    assert scored["searchability"] > 50
    assert scored["decision"] == "write_page"
    assert scored["score"] < 15


def test_a_self_hosted_product_promotes_the_same_operator_message(ranking):
    message = candidate("UPSTASH_REDIS_URL is not set", surface="operator")
    hosted = ranking["score_candidate"](message)
    self_hosted = ranking["score_candidate"](message, ranking["SELF_HOSTED_OPERATOR_WEIGHT"])
    assert self_hosted["score"] > 5 * hosted["score"]
    assert self_hosted["searchability"] == hosted["searchability"]


def test_an_operator_audience_of_nobody_reads_as_internal(ranking):
    scored = ranking["score_candidate"](
        candidate("UPSTASH_REDIS_URL is not set", surface="operator"), 0
    )
    assert scored["score"] == 0.0
    assert scored["decision"] == "internal_only"


@pytest.mark.parametrize("invalid", [-0.1, 1.1, True, "0.5"])
def test_operator_weight_is_validated(ranking, invalid):
    with pytest.raises(ValueError):
        ranking["score_candidate"](candidate("x", surface="operator"), invalid)
    with pytest.raises(ValueError):
        ranking["rank_candidates"]([candidate("x", surface="operator")], 15, invalid)


@pytest.mark.parametrize(
    "message",
    [
        "Error: {msg}",  # nothing invariant survives the placeholder
        "Invalid input",  # two generic words
        "%s failed",
        "${detail}",
        "",
        "   ",
        "Something went wrong",  # long enough, but every word is a stock error word
        "An unexpected error occurred. Please try again.",
    ],
)
def test_messages_a_user_could_never_find_score_zero(ranking, message):
    assert ranking["searchability"](message) == 0


def test_one_distinctive_word_is_enough_to_separate_a_query(ranking):
    found = ranking["searchability"]
    # "User" is not a stock error word; "Something went wrong" has nothing of its own.
    assert found("User not found") > 0
    assert found("Failed to redeploy") > 0
    assert found("Something went wrong") == 0


def test_placeholders_cost_a_message_its_searchable_core(ranking):
    found = ranking["searchability"]
    whole = found("Webhook signature verification failed for endpoint acct_live")
    split = found("Webhook signature verification failed for {endpoint} in {account}")
    assert whole > split > 0


@pytest.mark.parametrize(
    "message,expected",
    [
        ("ERR_CONN_REFUSED", ["ERR_CONN_REFUSED"]),
        ("failed with E402 downstream", ["E402"]),
        ("PGRST116: no rows returned", ["PGRST116"]),
        ("HTTP-502-UPSTREAM while proxying", ["HTTP-502-UPSTREAM"]),
        ("connection_pool_exhausted in handler", []),  # lowercase identifier, not a code
        ("E-MAIL address rejected", []),  # one separator and no digit
        ("HTTP 502 received", []),  # a bare status is not distinctive
    ],
)
def test_code_tokens_follow_conventions_and_reject_identifiers(ranking, message, expected):
    assert ranking["code_tokens"](message) == expected


def test_invariant_runs_drop_every_placeholder_dialect(ranking):
    runs = ranking["invariant_runs"]("a {0} b %(name)s c %d d ${x} e $name f <path> g")
    assert runs == ["a", "b", "c", "d", "e", "f", "g"]


def test_reach_weight_grows_with_call_sites_and_saturates(ranking):
    reach = ranking["reach_weight"]
    assert reach(0) == 0.0
    assert reach(1) < reach(2) < reach(3)
    assert reach(4) == 1.0 == reach(50)


@pytest.mark.parametrize("invalid", [-1, True, 1.5, "3", None])
def test_reach_weight_rejects_invalid_counts(ranking, invalid):
    with pytest.raises(ValueError):
        ranking["reach_weight"](invalid)


def test_an_internal_message_scores_zero_however_findable_it_is(ranking):
    scored = ranking["score_candidate"](
        candidate(
            "ERR_ASSERT_INVARIANT: ledger balance drifted mid-transaction", surface="internal"
        )
    )
    assert scored["searchability"] > 0
    assert scored["score"] == 0.0
    assert scored["decision"] == "internal_only"


def test_documented_coverage_removes_the_opportunity(ranking):
    message = "ERR_CONN_REFUSED: upstream database rejected the connection pool handshake"
    uncovered = ranking["score_candidate"](candidate(message))
    covered = ranking["score_candidate"](candidate(message, coverage="documented"))
    partial = ranking["score_candidate"](candidate(message, coverage="partial"))
    assert uncovered["decision"] == "write_page" and uncovered["score"] > 0
    assert covered["decision"] == "already_covered" and covered["score"] == 0.0
    assert 0 < partial["score"] < uncovered["score"]


def test_a_findable_message_nothing_reaches_is_not_an_opportunity(ranking):
    scored = ranking["score_candidate"](
        candidate("ERR_LEGACY_IMPORT: the v1 import endpoint was removed", call_sites=0)
    )
    assert scored["decision"] == "unreachable"
    assert scored["score"] == 0.0


@pytest.mark.parametrize(
    "broken",
    [
        {"surface": "api", "call_sites": 1, "coverage": "none"},  # no message
        candidate("x", surface="marketing"),
        candidate("x", coverage="maybe"),
    ],
)
def test_score_candidate_rejects_unusable_candidates(ranking, broken):
    with pytest.raises(ValueError):
        ranking["score_candidate"](broken)


def test_ranking_is_ordered_by_score_then_message(ranking):
    buckets = ranking["rank_candidates"](
        [
            candidate("ERR_BETA_TWO: connection pool handshake rejected upstream"),
            candidate("ERR_ALPHA_ONE: connection pool handshake rejected upstream"),
            candidate("The requested resource could not be found"),
            candidate("Invalid input"),
            candidate("Debug: {trace}", surface="internal"),
        ]
    )
    ordered = buckets["opportunities"]
    assert ordered == sorted(ordered, key=lambda item: (-item["score"], item["message"]))
    # Equal scores break on the message so repeated runs keep the same table.
    assert ordered[0]["message"].startswith("ERR_ALPHA_ONE")
    assert ordered[1]["message"].startswith("ERR_BETA_TWO")
    assert ordered[0]["score"] == ordered[1]["score"]
    assert [item["message"] for item in buckets["not_searchable"]] == ["Invalid input"]
    assert [item["message"] for item in buckets["internal_only"]] == ["Debug: {trace}"]


def test_the_cut_keeps_the_remainder_instead_of_dropping_it(ranking):
    candidates = [
        candidate(f"ERR_CODE_{index:02d}: the connection pool handshake was rejected upstream")
        for index in range(12)
    ]
    buckets = ranking["rank_candidates"](candidates, max_opportunities=5)
    assert len(buckets["opportunities"]) == 5
    assert len(buckets["deferred"]) == 7
    assert not {item["message"] for item in buckets["opportunities"]} & {
        item["message"] for item in buckets["deferred"]
    }


def test_rank_candidates_rejects_duplicates_and_unbounded_limits(ranking):
    with pytest.raises(ValueError):
        ranking["rank_candidates"](
            [candidate("Duplicate message here"), candidate("Duplicate message here")]
        )
    for limit in (0, 41, 2.5, True, "5"):
        with pytest.raises(ValueError):
            ranking["rank_candidates"]([candidate("Something findable happened upstream")], limit)
    with pytest.raises(ValueError):
        ranking["rank_candidates"]("not a list")


def test_manifest_declares_every_shipped_resource():
    definition = json.loads((PACKAGE / "workflow.json").read_text(encoding="utf-8"))["definition"]
    procedure = definition["procedure"]
    present = {
        path.relative_to(PACKAGE).as_posix()
        for path in (PACKAGE / "skills").rglob("*")
        if path.is_file()
    }
    assert set(procedure["skill_files"]) == present
    assert definition["key"] == PACKAGE.name
    assert (PACKAGE / procedure["prompt_path"]).is_file()
    entry = f"{procedure['skills_path']}/{procedure['entry_skill']}/SKILL.md"
    assert entry in procedure["skill_files"]


def test_the_report_contract_matches_the_headings_the_skill_promises():
    skill = (RESOURCES / "SKILL.md").read_text(encoding="utf-8")
    for heading in (
        "## Ranked opportunities",
        "## Below the cut",
        "## Already documented",
        "## Queries you cannot win",
        "## Internal only",
        "## What this does not measure",
        "## Method and coverage",
    ):
        assert heading in skill


def test_the_report_asks_for_a_page_and_not_only_a_finding():
    skill = (RESOURCES / "SKILL.md").read_text(encoding="utf-8")
    # The deliverable is a content shortlist; a table of code locations is not one.
    assert "suggested page" in skill.lower()
    assert "content.plan" in skill and "content.draft" in skill

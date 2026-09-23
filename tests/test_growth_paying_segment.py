"""Offline checks for growth.paying_segment against synthetic, Stripe-shaped subscriptions."""

import json
import runpy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from tin_lite.community import REPOSITORY_ROOT
from tin_lite.workflow_code import validate_code_definition, validate_code_result
from tin_lite.workflow_qualification import Qualification, assess_output

ROOT = REPOSITORY_ROOT / "workflow_packages" / "growth.paying_segment"
NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)
DAY = 86_400
LIMIT = 64_000


def package():
    definition = json.loads((ROOT / "workflow.json").read_text())["definition"]
    return SimpleNamespace(**runpy.run_path(str(ROOT / "main.py"))), definition


MODULE, DEFINITION = package()


def subscription(
    index,
    *,
    email,
    started_days_ago,
    paid_days=None,
    interval="month",
    amount=2900,
    trial_days=0,
    discount=False,
    reason=None,
    feedback=None,
    items=1,
    metadata=None,
    country="US",
    livemode=False,
):
    """A subscription with its customer expanded, in the shape and size Stripe returns."""
    start = int(NOW.timestamp()) - started_days_ago * DAY
    trial_end = start + trial_days * DAY if trial_days else None
    paid_start = trial_end or start
    ended = None if paid_days is None else paid_start + paid_days * DAY
    price = {
        "id": f"price_{interval}{amount}",
        "object": "price",
        "active": True,
        "billing_scheme": "per_unit",
        "created": start,
        "currency": "usd",
        "custom_unit_amount": None,
        "livemode": livemode,
        "lookup_key": None,
        "metadata": {},
        "nickname": None,
        "product": "prod_Synthetic01",
        "recurring": {
            "aggregate_usage": None,
            "interval": interval,
            "interval_count": 1,
            "meter": None,
            "trial_period_days": None,
            "usage_type": "licensed",
        },
        "tax_behavior": "unspecified",
        "tiers_mode": None,
        "transform_quantity": None,
        "type": "recurring",
        "unit_amount": amount,
        "unit_amount_decimal": str(amount),
    }
    plan = {
        "id": price["id"],
        "object": "plan",
        "active": True,
        "aggregate_usage": None,
        "amount": amount,
        "amount_decimal": str(amount),
        "billing_scheme": "per_unit",
        "created": start,
        "currency": "usd",
        "interval": interval,
        "interval_count": 1,
        "livemode": livemode,
        "metadata": {},
        "meter": None,
        "nickname": None,
        "product": "prod_Synthetic01",
        "tiers_mode": None,
        "transform_usage": None,
        "trial_period_days": None,
        "usage_type": "licensed",
    }
    sub_id = f"sub_{index:06d}"
    return {
        "id": sub_id,
        "object": "subscription",
        "application": None,
        "application_fee_percent": None,
        "automatic_tax": {"disabled_reason": None, "enabled": False, "liability": None},
        "billing_cycle_anchor": paid_start,
        "billing_cycle_anchor_config": None,
        "billing_thresholds": None,
        "cancel_at": ended,
        "cancel_at_period_end": False,
        "canceled_at": ended,
        "cancellation_details": {"comment": None, "feedback": feedback, "reason": reason},
        "collection_method": "charge_automatically",
        "created": start,
        "currency": "usd",
        "current_period_end": paid_start + 30 * DAY,
        "current_period_start": paid_start,
        "customer": {
            "id": f"cus_{index:06d}",
            "object": "customer",
            "address": {
                "city": None,
                "country": country,
                "line1": None,
                "line2": None,
                "postal_code": None,
                "state": None,
            },
            "balance": 0,
            "created": start,
            "currency": "usd",
            "default_source": None,
            "delinquent": False,
            "description": None,
            "discount": None,
            "email": email,
            "invoice_prefix": f"INV{index:05d}",
            "invoice_settings": {
                "custom_fields": None,
                "default_payment_method": "pm_synthetic",
                "footer": None,
                "rendering_options": None,
            },
            "livemode": livemode,
            "metadata": metadata or {},
            "name": f"Synthetic Customer {index}",
            "next_invoice_sequence": 2,
            "phone": None,
            "preferred_locales": [],
            "shipping": None,
            "tax_exempt": "none",
            "test_clock": None,
        },
        "days_until_due": None,
        "default_payment_method": "pm_synthetic",
        "default_source": None,
        "default_tax_rates": [],
        "description": None,
        "discount": None,
        "discounts": ["di_synthetic"] if discount else [],
        "ended_at": ended,
        "invoice_settings": {"account_tax_ids": None, "issuer": {"type": "self"}},
        "items": {
            "object": "list",
            "data": [
                {
                    "id": f"si_{index:06d}_{n}",
                    "object": "subscription_item",
                    "billing_thresholds": None,
                    "created": start,
                    "discounts": [],
                    "metadata": {},
                    "plan": plan,
                    "price": price,
                    "quantity": 1,
                    "subscription": sub_id,
                    "tax_rates": [],
                }
                for n in range(items)
            ],
            "has_more": False,
            "total_count": items,
            "url": f"/v1/subscription_items?subscription={sub_id}",
        },
        "latest_invoice": f"in_{index:06d}",
        "livemode": livemode,
        "metadata": {},
        "next_pending_invoice_item_invoice": None,
        "on_behalf_of": None,
        "pause_collection": None,
        "payment_settings": {
            "payment_method_options": None,
            "payment_method_types": None,
            "save_default_payment_method": "off",
        },
        "pending_invoice_item_interval": None,
        "pending_setup_intent": None,
        "pending_update": None,
        "schedule": None,
        "start_date": start,
        "status": "active" if ended is None else "canceled",
        "test_clock": None,
        "transfer_data": None,
        "trial_end": trial_end,
        "trial_settings": {"end_behavior": {"missing_payment_method": "create_invoice"}},
        "trial_start": start if trial_days else None,
    }


class FakeStripe:
    """Pages like GET /v1/subscriptions and enforces the gateway's raw response bound."""

    def __init__(self, subscriptions, status=200):
        self.subscriptions = sorted(subscriptions, key=lambda s: (-s["created"], s["id"]))
        self.status = status
        self.calls = []

    async def request(self, *, service, step, path, method="GET", params=None, body=None):
        assert (service, path, method, body) == ("stripe", "/v1/subscriptions", "GET", None)
        assert len(self.calls) < 8, "the declared service allows eight calls"
        assert step not in {s for s, _ in self.calls}, "step IDs must be stable and unique"
        assert all(isinstance(v, (str, int)) for v in params.values()), "scalar params only"
        self.calls.append((step, dict(params)))
        if self.status != 200:
            return {"status": self.status, "data": {"error": {"type": "invalid_request_error"}}}
        rows = [
            s
            for s in self.subscriptions
            if params["created[gte]"] <= s["created"] <= params["created[lte]"]
        ]
        if "starting_after" in params:
            ids = [s["id"] for s in rows]
            rows = rows[ids.index(params["starting_after"]) + 1 :]
        page = rows[: params["limit"]]
        data = {
            "object": "list",
            "data": page,
            "has_more": len(rows) > len(page),
            "url": "/v1/subscriptions",
        }
        if len(json.dumps(data, indent=2).encode()) > LIMIT:
            raise ValueError("oversized response")
        return {"status": 200, "data": data}


class Context(dict):
    def __init__(self, stripe):
        super().__init__(run_id="00000000-0000-4000-8000-000000000099", created_at=NOW.isoformat())
        self.services = stripe


async def run(subscriptions, **inputs):
    stripe = FakeStripe(subscriptions)
    result = await MODULE.run(Context(stripe), inputs)
    validate_code_result(json.dumps(result).encode(), validate_code_definition(DEFINITION))
    return result["content"], stripe


def evidence(content):
    return json.loads(content.split("<!-- tin-paying-segment-evidence-v1 -->\n```json\n")[1][:-5])


def ordinary():
    """25 work-email customers (20 stay, 12 of them annual) against 25 personal-email ones."""
    subs, index = [], 0
    for n in range(25):
        index += 1
        annual = n < 12
        subs.append(
            subscription(
                index,
                email=f"founder@studio{n}.io",
                started_days_ago=90 + n * 7,
                interval="year" if annual else "month",
                amount=29000 if annual else 2900,
                paid_days=None if n < 20 else 20,
                reason=None if n < 20 else "cancellation_requested",
                feedback=None if n < 20 else "missing_features",
                metadata={"source": "podcast" if n % 2 else "search"},
            )
        )
    for n in range(25):
        index += 1
        if n < 6:
            outcome = {}
        elif n < 18:
            outcome = {"paid_days": 25, "reason": "cancellation_requested"}
            outcome["feedback"] = "too_expensive"
        elif n < 22:
            outcome = {"trial_days": 14, "paid_days": -1, "reason": "cancellation_requested"}
        else:
            outcome = {"paid_days": 35, "reason": "payment_failed"}
        subs.append(
            subscription(
                index,
                email=f"person{n}@gmail.com",
                started_days_ago=91 + n * 7,
                metadata={"source": "podcast" if n % 2 else "search"},
                **outcome,
            )
        )
    return subs


def test_manifest_declares_a_read_only_stripe_binding_and_the_rendered_path():
    spec = validate_code_definition(DEFINITION)
    assert DEFINITION["integration_requirements"] == [
        {"provider_key": "custom.api.stripe", "capabilities": ["http.read"], "required": true}
        for true in [True]
    ]
    assert DEFINITION["code"]["services"]["stripe"]["max_calls"] == MODULE.MAX_CALLS
    assert DEFINITION["code"]["services"]["stripe"]["max_response_bytes"] == LIMIT
    assert DEFINITION["code"]["output"]["path"] == MODULE.OUTPUT
    assert "model_routes" not in DEFINITION["code"]
    assert spec is not None


async def test_ordinary_account_names_who_to_aim_at_and_hands_it_off():
    content, stripe = await run(
        ordinary(), exclude_domains=[], product_summary="An API for podcast clipping."
    )
    assert "Status: complete" in content
    assert "Data: Stripe TEST MODE" in content
    # Markdown merges single-newline lines; each finding must stay its own block.
    assert "\n- Status: complete\n- Generated:" in content
    assert "\n\nAim at:" in content and "\n\nStop paying to acquire:" in content
    assert "Aim at: people who sign up with a work email. 80% of them stayed" in content
    assert "Stop paying to acquire: people who sign up with a personal email" in content
    # Annual billing is a lever on the offer, never the acquisition target.
    assert "Offer lever: customers who pick annual billing kept paying at 100%" in content
    assert "objective: Shortlist people who look like the customers who paid and stayed" in content
    assert "buyer_context: An API for podcast clipping. The buyers who pay" in content
    assert "studio19.io" in content and "gmail.com" not in content
    assert "@" not in content.split("<!--")[0], "no email addresses in the human report"
    assert "switched" not in content and "too expensive 12" in content
    # Metadata "source" was discovered as a dimension but shows no real difference.
    assert "Metadata source: podcast" in content
    data = evidence(content)
    assert data["fetched"] == 50 and data["judged"] == 50 and not data["truncated"]
    first, *rest = stripe.calls
    assert first[0] == "probe" and first[1]["limit"] == 3
    assert first[1]["status"] == "all" and first[1]["expand[0]"] == "data.customer"
    assert first[1]["created[lte]"] == int(NOW.timestamp()) - 60 * DAY
    assert all(params["limit"] > 3 for _, params in rest)
    tests = {(t["family"], t["value"]): t for t in data["tests"]}
    # One price per interval: "Entry price" repeats "Billing interval" and is shown once.
    assert not any(family == "Entry price" for family, _ in tests)
    assert tests[("Email type", "work email")]["comparisons"] == 3
    assert tests[("Email type", "work email")]["p_holm"] < 0.05
    assert tests[("Metadata source", "podcast")]["p_holm"] > 0.05


def too_few():
    return ordinary()[:8] + ordinary()[25:33]


def no_difference():
    """Half of every segment stays: any named segment here would be a false finding."""
    return [
        subscription(
            n,
            email=f"a@team{n}.com" if n % 2 else f"p{n}@gmail.com",
            started_days_ago=100 + n * 5,
            paid_days=None if n % 4 < 2 else 20,
        )
        for n in range(40)
    ]


async def test_small_accounts_are_told_to_wait_instead_of_getting_a_segment():
    content, _ = await run(too_few())
    assert "Status: insufficient evidence" in content
    assert "Not enough customers to judge yet: 16 of the 20 needed." in content
    assert "## Hand-off" not in content and "Aim at:" not in content


async def test_no_real_difference_stays_provisional():
    content, _ = await run(no_difference())
    assert "Status: provisional" in content
    assert "Aim at:" not in content and "Stop paying to acquire:" not in content
    assert "objective: Provisional, test on a small batch:" in content or (
        "No segment keeps customers better" in content
    )


async def test_failed_payments_come_before_retargeting():
    subs = [
        subscription(
            n,
            email=f"a@team{n}.com" if n < 20 else f"p{n}@gmail.com",
            started_days_ago=100 + n * 5,
            paid_days=None if n % 3 else 30,
            reason=None if n % 3 else "payment_failed",
        )
        for n in range(40)
    ]
    content, _ = await run(subs)
    assert "Next action: fix failed payments before changing who you target." in content
    assert "a payment failed 14" in content


async def test_large_records_shrink_pages_and_disclose_truncation():
    subs = [
        subscription(n, email=f"a@team{n}.com", started_days_ago=100 + n, items=8)
        for n in range(200)
    ]
    content, stripe = await run(subs)
    limits = [params["limit"] for _, params in stripe.calls]
    assert len(stripe.calls) == 8 and limits[0] == 3 and max(limits[1:]) <= 4
    assert "Older subscriptions exist that this run could not read" in content
    assert "eight-request limit was reached" in content


async def test_refused_key_writes_a_setup_diagnostic_after_one_call():
    stripe = FakeStripe(ordinary(), status=401)
    result = await MODULE.run(Context(stripe), {})
    assert len(stripe.calls) == 1
    assert "Status: connection needs attention" in result["content"]
    assert "restricted key with Read access to Subscriptions and Customers" in result["content"]


def mutate(change):
    subs = ordinary()
    change(subs)
    return subs


@pytest.mark.parametrize(
    "subs",
    [
        mutate(lambda s: s[0].update(object="invoice")),
        mutate(lambda s: s[0].update(start_date="yesterday")),
        mutate(lambda s: s[0].pop("items")),
        mutate(
            lambda s: s[0]["items"]["data"][0].pop("price") and s[0]["items"]["data"][0].pop("plan")
        ),
        mutate(lambda s: s[1].update(id=s[0]["id"], created=s[0]["created"] - 1)),
    ],
    ids=["not-a-subscription", "bad-timestamp", "no-items", "no-price", "duplicate"],
)
async def test_plausible_but_malformed_stripe_data_fails_instead_of_reporting(subs):
    with pytest.raises(ValueError):
        await MODULE.run(Context(FakeStripe(subs)), {})


async def test_invalid_envelope_fails():
    class Broken(FakeStripe):
        async def request(self, **kwargs):
            await super().request(**kwargs)
            return {"status": 200, "data": {"object": "customer"}}

    with pytest.raises(ValueError, match="subscription list"):
        await MODULE.run(Context(Broken(ordinary())), {})


@pytest.mark.parametrize(
    "inputs",
    [
        {"lookback_days": 80},
        {"retention_days": 90, "lookback_days": 100},
        {"min_segment_size": 2},
        {"exclude_domains": ["not a domain"]},
        {"exclude_domains": [f"d{n}.com" for n in range(21)]},
        {"product_summary": "x" * 501},
    ],
)
async def test_invalid_inputs_are_rejected_before_any_request(inputs):
    stripe = FakeStripe(ordinary())
    with pytest.raises(ValueError):
        await MODULE.run(Context(stripe), inputs)
    assert stripe.calls == []


async def test_excluded_domains_and_identifying_metadata_never_become_segments():
    subs = ordinary()
    for sub in subs:
        sub["customer"]["metadata"]["referrer"] = sub["customer"]["email"]
        sub["customer"]["metadata"]["signup_id"] = "123456789"
    content, _ = await run(subs, exclude_domains=["studio0.io", "studio1.io"])
    assert "2 excluded by domain" in content
    human = content.split("<!--")[0]
    assert "studio0.io" not in human and "studio1.io" not in human
    assert "Metadata referrer" not in content and "Metadata signup_id" not in content


def test_outcome_rules_ignore_trial_days_and_wait_for_young_customers():
    now = int(NOW.timestamp())
    base = {"status": "active", "paid_start": now - 90 * DAY, "ended": None}
    assert MODULE.outcome(base, now, 60) == "stayed"
    assert MODULE.outcome({**base, "paid_start": now - 30 * DAY}, now, 60) == "too young"
    assert MODULE.outcome({**base, "ended": now - 70 * DAY}, now, 60) == "left"
    assert MODULE.outcome({**base, "ended": now - 20 * DAY}, now, 60) == "stayed"
    assert MODULE.outcome({**base, "ended": base["paid_start"]}, now, 60) == "never paid"
    assert MODULE.outcome({**base, "status": "incomplete_expired"}, now, 60) == "never paid"


def test_statistics_match_reference_values():
    # Fisher's tea-tasting style table; reference two-sided p from R's fisher.test.
    assert MODULE.fisher(1, 9, 11, 3) == pytest.approx(0.002759, abs=1e-6)
    assert MODULE.fisher(3, 1, 1, 3) == pytest.approx(0.485714, abs=1e-6)
    tests = [{"p": 0.01}, {"p": 0.04}, {"p": 0.03}]
    assert MODULE.holm(tests) == 3
    assert [t["p_holm"] for t in tests] == pytest.approx([0.03, 0.06, 0.06])
    # Two rows of one two-valued split are a single comparison.
    mirrored = [{"p": 0.01, "split": "a"}, {"p": 0.01, "split": "a"}, {"p": 0.04, "split": "b"}]
    assert MODULE.holm(mirrored) == 2
    assert [t["p_holm"] for t in mirrored] == pytest.approx([0.02, 0.02, 0.04])
    low, high = MODULE.wilson(8, 10)
    assert low == pytest.approx(0.4902, abs=1e-4) and high == pytest.approx(0.9433, abs=1e-4)


def test_price_handles_api_versions_and_usage_prices():
    monthly, currency, label, interval = MODULE.price(
        [{"plan": {"amount": 12000, "currency": "eur", "interval": "year", "interval_count": 1}}],
        None,
    )
    assert (monthly, currency, label, interval) == (1000, "eur", "EUR 120.00/year", "year")
    metered = [
        {"price": {"unit_amount": None, "currency": "usd", "recurring": {"interval": "month"}}}
    ]
    assert MODULE.price(metered, "usd")[0] is None


CASE_FIXTURES = {
    "ordinary": (ordinary, 200),
    "too_few_customers": (too_few, 200),
    "no_real_difference": (no_difference, 200),
    "refused_key": (ordinary, 401),
}


async def test_qualification_cases_pass_on_their_fixtures():
    raw = REPOSITORY_ROOT / "workflow_evals" / "growth.paying_segment" / "qualification.json"
    qualification = Qualification.model_validate_json(raw.read_text())
    assert {case.id for case in qualification.cases} == set(CASE_FIXTURES)
    for case in qualification.cases:
        build, status = CASE_FIXTURES[case.id]
        result = await MODULE.run(Context(FakeStripe(build(), status=status)), case.inputs)
        report = assess_output(case, status="succeeded", content=result["content"].encode())
        assert report["status"] == "passed", (case.id, report["checks"])

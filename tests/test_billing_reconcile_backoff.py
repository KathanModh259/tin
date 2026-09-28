"""Pending checkouts are reread on a per-payment backoff; no real Stripe requests."""

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs
from uuid import UUID, uuid4

import httpx
from pydantic import SecretStr
from test_billing import billed as billed
from test_private_workflows import ACTOR
from test_procedure_publication import publication_db as publication_db

from tin_lite.billing_payments import CHECKOUT_LIFETIME, StripePayments, reconcile_interval

MIGRATION = Path(__file__).parents[1] / "migrations" / "048_billing_reconcile_backoff.sql"


def test_reconcile_interval_backs_off_by_payment_age():
    schedule = [
        (timedelta(seconds=30), timedelta(seconds=30)),
        (timedelta(seconds=119), timedelta(seconds=30)),
        (timedelta(minutes=2), timedelta(minutes=2)),
        (timedelta(minutes=9), timedelta(minutes=2)),
        (timedelta(minutes=10), timedelta(minutes=10)),
        (timedelta(minutes=59), timedelta(minutes=10)),
        (timedelta(hours=1), timedelta(minutes=30)),
        (timedelta(days=3), timedelta(minutes=30)),
    ]
    for age, interval in schedule:
        assert reconcile_interval(age) == interval, age
    # A lost completion webhook for a fresh checkout is still read within about a minute.
    assert reconcile_interval(timedelta(seconds=30)) <= timedelta(minutes=1)


def test_checkout_lifetime_is_within_stripe_bounds():
    # Stripe accepts 30 minutes to 24 hours; keep a retry margin above the minimum.
    assert timedelta(minutes=31) <= CHECKOUT_LIFETIME <= timedelta(hours=1)


def test_migration_adds_nullable_schedule_only():
    sql = MIGRATION.read_text()
    assert "ALTER TABLE billing_payments ADD COLUMN IF NOT EXISTS next_reconcile_at" in sql
    assert "NOT NULL" not in sql and "UPDATE" not in sql and "DELETE" not in sql


async def test_shared_client_serves_stripe_requests():
    seen = []

    def wire(request):
        seen.append(request)
        return httpx.Response(200, json={"id": "cs_test_1"})

    settings = SimpleNamespace(billing_test_enabled=True, stripe_secret_key=SecretStr("sk_test_x"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(wire)) as client:
        payments = StripePayments(
            billing=SimpleNamespace(db=None), settings=settings, client=client
        )
        for _ in range(2):
            assert await payments.request("GET", "checkout/sessions/cs_test_1") == {
                "id": "cs_test_1"
            }
        assert not client.is_closed
    assert len(seen) == 2
    assert seen[0].headers["Authorization"] == "Bearer sk_test_x"


async def test_checkout_sends_expiry_derived_from_the_durable_request(billed):
    f = billed
    payment = await f.payments.checkout(
        workspace_id=f.project.workspace_id, actor=ACTOR, amount_cents=2500, request_id=uuid4()
    )
    created = await f.db.pool.fetchval(
        "SELECT created_at FROM billing_payments WHERE id=$1", UUID(payment["id"])
    )
    [create] = [c for c in f.calls if c.url.path.endswith("/checkout/sessions")]
    data = parse_qs(create.content.decode())
    assert int(data["expires_at"][0]) == int((created + CHECKOUT_LIFETIME).timestamp())


def session(payment, status, payment_status):
    return {
        "id": f"cs_test_{payment['id']}",
        "livemode": False,
        "currency": "usd",
        "amount_total": 2500,
        "mode": "payment",
        "status": status,
        "payment_status": payment_status,
        "payment_intent": f"pi_{payment['id']}" if payment_status == "paid" else None,
        "metadata": {"tin_product": "tin-lite", "tin_payment_id": payment["id"]},
    }


async def pending_checkout(f, age=timedelta(minutes=1)):
    payment = await f.payments.checkout(
        workspace_id=f.project.workspace_id, actor=ACTOR, amount_cents=2500, request_id=uuid4()
    )
    await f.db.pool.execute(
        "UPDATE billing_payments SET created_at=now()-$2 WHERE id=$1",
        UUID(payment["id"]),
        age,
    )
    return payment


def wire_for(f, states):
    reads = []

    def wire(request):
        assert request.method == "GET"
        payment_id = request.url.path.removeprefix("/v1/checkout/sessions/cs_test_")
        reads.append(payment_id)
        return httpx.Response(200, json=session({"id": payment_id}, *states[payment_id]))

    f.payments.transport = httpx.MockTransport(wire)
    return reads


async def make_due(f, payment):
    await f.db.pool.execute(
        "UPDATE billing_payments SET next_reconcile_at=now()-interval '1 second' WHERE id=$1",
        UUID(payment["id"]),
    )


async def test_open_checkout_is_reread_later_not_every_pass(billed):
    f = billed
    f.settings.codex_api_projects = {f.project.id}
    payment = await pending_checkout(f)
    states = {payment["id"]: ("open", "unpaid")}
    reads = wire_for(f, states)
    await f.payments.reconcile()
    await f.payments.reconcile()
    await f.payments.reconcile()
    assert reads == [payment["id"]]
    delay = await f.db.pool.fetchval(
        "SELECT next_reconcile_at-now() FROM billing_payments WHERE id=$1", UUID(payment["id"])
    )
    assert timedelta(seconds=25) < delay <= timedelta(seconds=30)
    assert (
        await f.db.pool.fetchval(
            "SELECT status FROM billing_payments WHERE id=$1", UUID(payment["id"])
        )
        == "pending"
    )

    # Once due, the same checkout is read again; a lost completion still credits once.
    states[payment["id"]] = ("complete", "paid")
    await make_due(f, payment)
    await f.payments.reconcile()
    await make_due(f, payment)
    await f.payments.reconcile()
    assert reads == [payment["id"], payment["id"]]
    assert (await f.billing.overview(f.project.id, ACTOR))["available_usd"] == "25.00"
    assert await f.db.pool.fetchval("SELECT count(*) FROM billing_ledger") == 1


async def test_older_open_checkout_waits_longer(billed):
    f = billed
    payment = await pending_checkout(f, age=timedelta(minutes=20))
    wire_for(f, {payment["id"]: ("open", "unpaid")})
    await f.payments.reconcile()
    delay = await f.db.pool.fetchval(
        "SELECT next_reconcile_at-now() FROM billing_payments WHERE id=$1", UUID(payment["id"])
    )
    assert timedelta(minutes=9) < delay <= timedelta(minutes=10)


async def test_only_due_payments_are_read(billed):
    f = billed
    later = await pending_checkout(f, age=timedelta(minutes=3))
    due = await pending_checkout(f, age=timedelta(minutes=2))
    await f.db.pool.execute(
        "UPDATE billing_payments SET next_reconcile_at=now()+interval '5 minutes' WHERE id=$1",
        UUID(later["id"]),
    )
    reads = wire_for(f, {later["id"]: ("open", "unpaid"), due["id"]: ("open", "unpaid")})
    await f.payments.reconcile()
    assert reads == [due["id"]]


async def test_expired_checkout_is_terminal_and_not_reread(billed):
    f = billed
    payment = await pending_checkout(f, age=timedelta(minutes=50))
    reads = wire_for(f, {payment["id"]: ("expired", "unpaid")})
    await f.payments.reconcile()
    await make_due(f, payment)
    await f.payments.reconcile()
    assert reads == [payment["id"]]
    assert (
        await f.db.pool.fetchval(
            "SELECT status FROM billing_payments WHERE id=$1", UUID(payment["id"])
        )
        == "expired"
    )
    assert await f.db.pool.fetchval("SELECT count(*) FROM billing_ledger") == 0

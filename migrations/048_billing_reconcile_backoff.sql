-- Pending checkouts are reread from Stripe on a per-payment schedule instead of every
-- reconciliation pass. NULL means due now, so existing pending rows are read once and then
-- scheduled. No financial history changes. Idempotent.
ALTER TABLE billing_payments ADD COLUMN IF NOT EXISTS next_reconcile_at timestamptz;

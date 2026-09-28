-- Hosted default policies now include standing schedule authority equal to the $10 per-run
-- default. Backfill only policies nobody has edited: still at revision 1 with the exact hosted
-- defaults and no scheduling allowance. Saving limits in Billing raises the revision, so a
-- policy an admin changed (including clearing the allowance) is left alone. Idempotent.
UPDATE billing_project_policies
SET schedule_max_nanos = 10000000000, updated_at = now()
WHERE schedule_max_nanos IS NULL
  AND revision = 1
  AND per_run_nanos = 10000000000
  AND monthly_nanos = 10000000000
  AND concurrency = 1;

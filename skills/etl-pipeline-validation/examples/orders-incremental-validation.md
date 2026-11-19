# Example: incremental orders load with a boundary defect (synthetic)

All data in this example is synthetic, written for illustration.

## Context

- Pipeline: hourly incremental load from `src.orders` to `dw.fact_orders`.
- Watermark: maximum `updated_at` loaded so far, stored per run.
- Grain: one row per `order_id` (latest state; upsert on `order_id`).
- Window validated: `[2026-03-01 10:00, 2026-03-01 11:00)` UTC, run 7731.
- Freshness expectation: data through the previous hour, loaded within 15
  minutes after the hour.

## Synthetic source rows in the window

| order_id | updated_at (UTC) | order_date | amount | status |
|----------|------------------|------------|--------|--------|
| 501 | 2026-03-01 10:00:00 | 2026-03-01 | 40.00 | open |
| 502 | 2026-03-01 10:14:09 | 2026-03-01 | 15.50 | open |
| 503 | 2026-03-01 10:31:44 | 2026-02-28 | 99.90 | paid |
| 504 | 2026-03-01 10:59:59 | 2026-03-01 | 12.00 | test |

All amounts are in EUR. Order 504 has status `test`; the specification says test orders are
filtered out. Order 503 is a late-arriving record (event date in the
previous day).

## Observed results

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Schema contract | passed | `information_schema.columns` matches contract v3 (12 columns, types and nullability equal) |
| 2 | Volume reconciliation | failed | Source 4; loaded 2; filtered 1 (504, rule "exclude test"); rejected 0; unexplained 1 |
| 3 | Key differences | failed | `EXCEPT` query: 501 in source window, absent in target |
| 4 | Business key uniqueness | passed | Duplicate-key query returned 0 rows |
| 5 | Referential integrity | passed | 0 orphan `customer_key` values |
| 6 | Late-arriving record | passed | 503 present with `order_date` 2026-02-28 and amount 99.90 |
| 7 | Aggregate reconciliation | failed | 2026-03-01 / EUR: source 55.50 (excluding test), target 15.50 |
| 8 | Freshness | passed | `data_through` 10:31:44; run finished 11:06 |
| 9 | Idempotency | not run | No non-production environment available for a re-run |

## Diagnosis

- **Observed:** the previous run's stored watermark is `2026-03-01 10:00:00`.
  The run log shows the extraction predicate `updated_at > :watermark`.
- **Inferred (high confidence):** a record updated exactly at the watermark
  timestamp but committed after the previous extraction read is skipped by the
  strict `>` comparison. Order 501 is such a record. The defect is in the
  pipeline, not the source.
- **Proposed fix (not applied):** extract with `updated_at >= :watermark` and
  rely on the upsert to make the overlap idempotent, or use an overlap window
  (for example, re-read the last few minutes) sized from observed commit
  delays. Either needs a re-run test to confirm no duplicates.

## Acceptance decision

Not accepted. Re-validate after the fix with: a boundary record at the exact
watermark, a re-run of the same window in a test environment (fingerprints
equal), and a full-table count and amount reconciliation for March.

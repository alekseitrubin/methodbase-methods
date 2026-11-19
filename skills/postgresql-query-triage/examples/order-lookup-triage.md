# Example: slow order lookup (synthetic)

All tables, values and plan output below are synthetic and simplified for
illustration. They were written for this example, not captured from a real
system. Real plans contain more detail.

## Input

- Query, run by an API endpoint with parameters `$1 = 4211`, `$2 = 'open'`:

  ```sql
  SELECT o.id, o.created_at, o.total
  FROM orders o
  WHERE o.customer_id = $1 AND o.status = $2
  ORDER BY o.created_at DESC
  LIMIT 20;
  ```

- Symptom: endpoint p95 rose from about 40 ms to about 900 ms after a bulk
  import last week (from application monitoring).
- Environment: PostgreSQL 16, staging copy restored from last night's backup
  (same row counts as production).
- Indexes: `orders_pkey (id)`, `orders_customer_id_idx (customer_id)`.

## Evidence collected

Plain `EXPLAIN` on staging (safe; estimates only) showed an index scan on
`orders_customer_id_idx` with an estimated 8 rows. With authorization,
`EXPLAIN (ANALYZE, BUFFERS)` on staging, warm cache, three runs:

```text
Limit (actual time=612.4..612.5 rows=20 loops=1)
  -> Sort (actual time=612.4..612.4 rows=20 loops=1)
        Sort Key: created_at DESC
        Sort Method: top-N heapsort
        -> Index Scan using orders_customer_id_idx on orders o
              (cost=0.43..35.10 rows=8 width=24)
              (actual time=0.05..598.7 rows=41230 loops=1)
              Index Cond: (customer_id = 4211)
              Filter: (status = 'open')
              Rows Removed by Filter: 118904
              Buffers: shared hit=21410 read=96233
Execution Time: 612.9 ms
```

Runs: 598, 612 and 631 ms. `pg_stat_user_tables` showed `last_autoanalyze`
before the import and `n_mod_since_analyze` of about 3.1 million.
`pg_stats` for `customer_id` did not list 4211 among the most common values.

## Triage report

**Classification:** latency, inside the database (no lock waits observed in
`pg_stat_activity` during the runs).

**Observed**

- Index scan estimate 8 rows; actual 41,230 rows returned and 118,904 rows
  removed by the `status` filter.
- About 117,600 buffers touched for 20 output rows; 96,233 read from outside
  shared buffers.
- Statistics are older than the bulk import.

**Inferred (confidence: medium-high)**

- The import made customer 4211 (and likely others) much larger than the
  statistics show, so the planner expects a tiny index range.
- The index serves only `customer_id`; `status` and the ordering are applied
  after reading all of the customer's rows.

**Proposed (not yet applied; each needs authorization)**

1. Run `ANALYZE orders;` on staging and re-capture the plan. Low risk;
   confirms or rejects the statistics hypothesis.
2. If the plan still reads all rows of the customer, evaluate an index on
   `(customer_id, status, created_at DESC)`. Before proposing it for
   production, check write volume on `orders`, existing index count and
   whether `orders_customer_id_idx` becomes redundant. Create with
   `CREATE INDEX CONCURRENTLY` in production.
3. Investigate why autovacuum's analyze did not run after the import (for
   example, the import finished shortly before the incident window).

**Acceptance criteria (agreed with the requester)**

- On staging, same parameters, warm cache, five runs: median below 20 ms and
  the plan reads at most a few hundred buffers.
- The top 10 statements by total time on `orders` show no regression above
  10% in a load test.
- Production p95 for the endpoint returns below 60 ms for 24 hours.

**Not checked**

- Production plan (only staging was measured).
- Behavior with the generic plan the application's driver may use.

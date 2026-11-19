# Validation check patterns

Supporting reference for the `etl-pipeline-validation` Method. Queries use
PostgreSQL syntax and synthetic table names: `src.orders` (source extract),
`dw.fact_orders` (target), `dw.dim_customer` (dimension). All are read-only.
Adapt names, types and the window predicate to the pipeline.

Throughout, `:window_start` and `:window_end` delimit the validated window
as a half-open interval `[start, end)`.

## Schema contract

```sql
SELECT column_name, data_type, character_maximum_length,
       numeric_precision, numeric_scale, is_nullable
FROM information_schema.columns
WHERE table_schema = 'dw' AND table_name = 'fact_orders'
ORDER BY ordinal_position;
```

Compare with the contract column by column; report missing, extra and
changed columns separately.

## Volume reconciliation

```sql
SELECT 'source' AS side, count(*) AS row_count
FROM src.orders
WHERE updated_at >= :window_start AND updated_at < :window_end
UNION ALL
SELECT 'target', count(*)
FROM dw.fact_orders
WHERE source_updated_at >= :window_start AND source_updated_at < :window_end
UNION ALL
SELECT 'rejected', count(*)
FROM dw.rejected_orders
WHERE run_id = :run_id;
```

## Key-level differences

Keys in the source window missing from the target, and the reverse:

```sql
SELECT order_id FROM src.orders
WHERE updated_at >= :window_start AND updated_at < :window_end
EXCEPT
SELECT order_id FROM dw.fact_orders;

SELECT order_id FROM dw.fact_orders
WHERE source_updated_at >= :window_start AND source_updated_at < :window_end
EXCEPT
SELECT order_id FROM src.orders;
```

## Nullability and null rates

```sql
SELECT count(*)                                  AS row_count,
       count(*) FILTER (WHERE customer_key IS NULL) AS null_customer_key,
       count(*) FILTER (WHERE amount IS NULL)       AS null_amount,
       round(avg((discount_code IS NULL)::int), 4)  AS discount_code_null_rate
FROM dw.fact_orders
WHERE load_date = :load_date;
```

Compare optional-column null rates with recent loads rather than with a fixed
universal threshold.

## Uniqueness and duplicates

```sql
-- Business key duplicates at the declared grain.
SELECT order_id, count(*) AS copies
FROM dw.fact_orders
GROUP BY order_id
HAVING count(*) > 1
ORDER BY copies DESC
LIMIT 50;

-- Were the duplicates already in the source?
SELECT order_id, count(*) AS copies
FROM src.orders
GROUP BY order_id
HAVING count(*) > 1;
```

## Referential integrity

```sql
SELECT f.customer_key, count(*) AS orphan_rows
FROM dw.fact_orders AS f
LEFT JOIN dw.dim_customer AS d ON d.customer_key = f.customer_key
WHERE d.customer_key IS NULL
GROUP BY f.customer_key;
```

If the design maps unknown references to a placeholder member (for example
key `-1`), count those separately and report them; they are not orphans but
may still indicate late-arriving dimension data.

## Domain validity

```sql
SELECT status, count(*)
FROM dw.fact_orders
WHERE status NOT IN ('open', 'paid', 'shipped', 'cancelled')
GROUP BY status;

SELECT count(*) FILTER (WHERE amount < 0)                 AS negative_amounts,
       count(*) FILTER (WHERE order_date > current_date)  AS future_dates
FROM dw.fact_orders;
```

## Completeness by expected calendar

```sql
SELECT d::date AS expected_day
FROM generate_series(:window_start::date, :window_end::date - 1, interval '1 day') AS d
EXCEPT
SELECT DISTINCT order_date FROM dw.fact_orders;
```

## Freshness

```sql
SELECT max(source_updated_at) AS data_through,
       max(loaded_at)         AS last_loaded_at
FROM dw.fact_orders;
```

## Aggregate reconciliation

```sql
WITH s AS (
  SELECT order_date, currency, sum(amount) AS amount, count(*) AS n
  FROM src.orders
  WHERE status <> 'test'          -- documented filter rule
  GROUP BY order_date, currency
), t AS (
  SELECT order_date, currency, sum(amount) AS amount, count(*) AS n
  FROM dw.fact_orders
  GROUP BY order_date, currency
)
SELECT coalesce(s.order_date, t.order_date) AS order_date,
       coalesce(s.currency, t.currency)     AS currency,
       s.n AS source_n, t.n AS target_n,
       s.amount AS source_amount, t.amount AS target_amount,
       t.amount - s.amount AS difference
FROM s FULL OUTER JOIN t USING (order_date, currency)
WHERE s.n IS DISTINCT FROM t.n
   OR abs(coalesce(t.amount, 0) - coalesce(s.amount, 0)) > :tolerance;
```

## Row fingerprints for idempotency

Capture before and after a re-run of the same batch, in a non-production
environment:

```sql
SELECT count(*) AS row_count,
       count(DISTINCT order_id) AS distinct_keys,
       sum(amount) AS total_amount,
       md5(string_agg(md5(row(order_id, customer_key, amount, status)::text), ''
                      ORDER BY order_id)) AS content_hash
FROM dw.fact_orders
WHERE load_date = :load_date;
```

Identical results before and after indicate the re-run did not change the
state for these columns. Exclude columns that legitimately change on re-run
(for example `loaded_at`) and say so in the report. Aggregating a hash over
a very large table is expensive; restrict it to the window.

## Incremental window boundary

```sql
-- Records exactly at the boundary must appear exactly once.
SELECT order_id, count(*)
FROM dw.fact_orders
WHERE source_updated_at = :window_start
GROUP BY order_id;

-- Late-arriving records: event time in an earlier window, arrival in this one.
SELECT count(*)
FROM src.orders
WHERE updated_at >= :window_start AND updated_at < :window_end
  AND order_date < :window_start::date;
```

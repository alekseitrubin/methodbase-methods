# Read-only diagnostic queries

Supporting reference for the `postgresql-query-triage` Method. All queries
here only read catalog and statistics views. Visibility of other sessions'
query text and some statistics depends on role privileges (for example
membership in `pg_read_all_stats`). Column names vary across major versions;
adjust to the version in use.

Replace `public.orders` with the table under investigation.

## Version and settings

```sql
SELECT version();

SELECT name, setting, unit, source
FROM pg_settings
WHERE name IN ('work_mem', 'shared_buffers', 'effective_cache_size',
               'random_page_cost', 'default_statistics_target',
               'plan_cache_mode', 'jit', 'max_parallel_workers_per_gather');
```

## Session safety for measurement

Limit how long an authorized measurement may run, for this transaction only:

```sql
BEGIN;
SET LOCAL statement_timeout = '30s';
SET LOCAL lock_timeout = '2s';
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;   -- read-only statement only
ROLLBACK;
```

For an authorized modifying statement the same `BEGIN ... ROLLBACK` wrapper
discards the data changes, but not sequence increments, external effects, the
load generated or locks held while it ran.

## Workload: pg_stat_statements

Requires the extension to be installed and loaded. Columns shown are for
PostgreSQL 13 and later.

```sql
SELECT queryid,
       calls,
       round(total_exec_time::numeric, 1) AS total_ms,
       round(mean_exec_time::numeric, 2)  AS mean_ms,
       rows,
       shared_blks_hit,
       shared_blks_read,
       temp_blks_written,
       left(query, 120) AS query_start
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

Sort by `total_exec_time` for throughput problems and by `mean_exec_time`
for latency problems. Statistics accumulate since the last reset; record
`stats_reset` from `pg_stat_statements_info` (PostgreSQL 14 and later) so
the time window is known.

## Activity, waits and blocking

```sql
SELECT pid,
       usename,
       state,
       wait_event_type,
       wait_event,
       now() - xact_start  AS xact_age,
       now() - query_start AS query_age,
       pg_blocking_pids(pid) AS blocked_by,
       left(query, 120) AS query_start
FROM pg_stat_activity
WHERE backend_type = 'client backend'
  AND state <> 'idle'
ORDER BY xact_start NULLS LAST;
```

Look for sessions with non-empty `blocked_by`, long `xact_age`, and
`idle in transaction` sessions holding locks.

```sql
SELECT l.locktype, l.relation::regclass, l.mode, l.granted, l.pid
FROM pg_locks AS l
WHERE l.relation = 'public.orders'::regclass;
```

## Table health and statistics freshness

```sql
SELECT relname, n_live_tup, n_dead_tup, n_mod_since_analyze,
       last_analyze, last_autoanalyze, last_vacuum, last_autovacuum
FROM pg_stat_user_tables
WHERE relid = 'public.orders'::regclass;

SELECT pg_size_pretty(pg_table_size('public.orders'))   AS table_size,
       pg_size_pretty(pg_indexes_size('public.orders')) AS indexes_size;
```

## Column statistics

```sql
SELECT attname, null_frac, n_distinct, correlation,
       most_common_vals, most_common_freqs
FROM pg_stats
WHERE schemaname = 'public' AND tablename = 'orders'
  AND attname IN ('customer_id', 'status', 'created_at');
```

`n_distinct` negative means a fraction of the row count. `correlation` near
1 or -1 means physical order follows the column, which favors index range
scans.

## Existing indexes and their use

```sql
SELECT indexrelid::regclass AS index_name,
       pg_get_indexdef(indexrelid) AS definition,
       idx_scan,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE relid = 'public.orders'::regclass
ORDER BY idx_scan;

SELECT indexrelid::regclass, indisvalid, indisready
FROM pg_index
WHERE indrelid = 'public.orders'::regclass AND NOT indisvalid;
```

An index with `idx_scan = 0` since the last statistics reset may be unused on
this server, but may still be used on replicas or by rare jobs. Do not
recommend dropping it from this evidence alone.

## Extended statistics

```sql
SELECT statistics_name, attnames, kinds
FROM pg_stats_ext
WHERE schemaname = 'public' AND tablename = 'orders';
```

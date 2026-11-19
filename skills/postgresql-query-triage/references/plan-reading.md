# Reading PostgreSQL plans

Supporting reference for the `postgresql-query-triage` Method. Behavior can
vary by major version; confirm details in the PostgreSQL documentation for
the version in use.

## Structure

- A plan is a tree. Each node consumes rows from its children. Read from the
  most indented nodes outward.
- `cost=startup..total` is in arbitrary planner units, not milliseconds. It is
  useful for comparing alternatives within one plan, not across servers.
- `rows` in the cost section is the planner's *estimate* of rows output per
  execution of the node; `width` is estimated average row width in bytes.
- With `ANALYZE`, `actual time=first..last` is in milliseconds and, like
  `actual rows`, is an **average per loop**. Total rows from a node is
  approximately `actual rows x loops`; total time spent is approximately
  `last x loops`. Recent versions may show fractional average rows.
- Inclusive timing: a parent's time includes its children's. The node that
  *adds* the most time over its children is where work happens.
- `TIMING OFF` reduces instrumentation overhead when per-node timing is not
  needed; per-node timing itself can inflate execution time on some systems.

## Estimates versus actual rows

Compare estimated `rows` with `actual rows` (per loop) node by node.

- Small errors are normal. What matters is an error large enough to change a
  decision: join method, join order, scan type, or memory sizing.
- Errors usually originate low in the tree and compound upward through joins.
  Find the *lowest* node with a large error.
- Common causes:
  - statistics are stale (`last_analyze` / `last_autoanalyze` old, many
    modifications since);
  - correlated columns: the planner multiplies selectivities as if columns
    were independent. Extended statistics (`CREATE STATISTICS` with
    `dependencies`, `ndistinct` or `mcv`) can help;
  - skewed values not captured by the most-common-values list; raising the
    column statistics target can help;
  - predicates the planner cannot estimate well: expressions on columns,
    functions, type casts, `LIKE` patterns with leading wildcards,
    comparisons between columns;
  - parameters in generic prepared plans.

## Scans

| Node | Meaning | Watch for |
|------|---------|-----------|
| Seq Scan | Reads the whole table | Fine for large result fractions or small tables; suspicious when few rows survive a selective filter |
| Index Scan | Walks the index, visits the heap per match | `Rows Removed by Filter` (index serves only part of the predicate) |
| Index Only Scan | Answers from the index when pages are all-visible | `Heap Fetches` high: visibility map not current (vacuum) |
| Bitmap Index Scan + Bitmap Heap Scan | Collects matching locations, then reads pages in order | `Recheck Cond`, `lossy` heap blocks (bitmap exceeded `work_mem`) |

## Joins

| Node | Good when | Risk |
|------|-----------|------|
| Nested Loop | Outer side small and inner side indexed | Outer row count underestimated: inner work repeats many times |
| Hash Join | Larger unsorted inputs, equality join | Hash larger than memory: `Batches` greater than 1, temp I/O |
| Merge Join | Inputs already sorted or cheaply sortable | Expensive sorts added just to merge |

## Buffers

With `BUFFERS` (included by default with `ANALYZE` on PostgreSQL 18 and
later):

- `shared hit` - pages found in PostgreSQL shared buffers.
- `shared read` - pages requested from the operating system; may still be
  served from the OS page cache, so "read" does not prove physical I/O.
- `shared dirtied` / `written` - pages modified or written by this query.
- `temp read` / `written` - spills of sorts, hashes or materialization.
- Each buffer is a block (8 kB by default). Multiply to estimate volume.

A query reading far more buffers than the size of its result suggests wasted
reading (missing or partial index, bloat, wide rows).

## Other signals

- `Sort Method: external merge Disk: ...` - sort exceeded `work_mem`.
- `Memoize` hit/miss counts (PostgreSQL 14 and later) - repeated inner lookups
  cached.
- `Parallel` nodes and `Workers Launched` lower than `Workers Planned` -
  parallel workers were unavailable.
- `Planning Time` large relative to execution - many partitions, many
  joins, or heavy planning; consider prepared statements and partition
  pruning.
- `JIT` section - compilation time on a short query can exceed the benefit.
- `Subplan` executed per row - often rewritable as a join.

## Plan stability

- Record the PostgreSQL version and relevant settings (`EXPLAIN (SETTINGS)`,
  PostgreSQL 12 and later) together with every plan.
- The same query can get different plans for different parameter values.
  Capture plans for representative and worst-case values.
- The `auto_explain` module can log plans of slow statements in production;
  enabling `auto_explain.log_analyze` adds overhead to every statement and
  requires authorization.

---
name: etl-pipeline-validation
description: >-
  Validates data pipelines between source, transformation and target with a
  repeatable evidence-based workflow: schema contracts, row-count and value
  reconciliation, nullability, uniqueness, duplicates, referential integrity,
  completeness, freshness, transformation accuracy, incremental loading,
  idempotency, late-arriving data and error handling, ending in a validation
  report. Use when testing a new or changed ETL/ELT job, investigating
  missing, duplicated or wrong data in a warehouse table, or defining
  acceptance checks for a pipeline release.
license: MIT
metadata:
  version: "0.1.0"
  maturity: ready-for-review
---

# ETL Pipeline Validation

## Purpose

Establish, with evidence, whether a pipeline delivers the data its consumers
expect: the right records, once, with correct values, on time, and
reproducibly on re-run. The outcome is a validation report listing every
check, its result and its evidence, with failures and unverified areas
explicit.

## When to use

- Accepting a new pipeline or a change to an existing one.
- Investigating a data incident (missing rows, duplicates, wrong totals,
  stale data).
- Defining automated checks and thresholds for a recurring load.
- Verifying a backfill, reprocessing or migration between systems.

## When not to use

- Validating the business correctness of source data itself (for example,
  whether sales figures are true). This Method checks that the pipeline
  preserves and transforms data as specified.
- Performance tuning of the pipeline; see a performance Method instead.
- Data privacy or access reviews, which need their own process.

## Inputs and prerequisites

| Input | Required | If missing |
|-------|----------|------------|
| Pipeline description: sources, targets, schedule, load type (full or incremental) | Yes | Ask. |
| Target schema contract: columns, types, nullability, keys, grain (one row per what?) | Yes | Ask. If no contract exists, draft one from the specification and get it confirmed before validating against it. |
| Transformation rules / mapping specification | Yes for accuracy checks | Mark accuracy checks *not run*; do not infer rules from code alone without saying so. |
| Freshness expectation (for example, "loaded by 06:00 UTC with data through yesterday") | Yes for freshness | Ask. |
| Read access to source and target, or extracts of both | Yes | Ask for read-only access or extracts. Never request write access to validate. |
| Batch or window identifiers (load date, watermark, run ID) | For incremental | Ask how loads are delimited. |

Prerequisites: read-only roles on source and target; a scratch area for
temporary comparison tables if comparisons cannot be done in place (created
only with permission).

## Safety rules

- Validation is read-only. Do not "fix" data in the target while validating.
  Propose fixes separately.
- Re-running a load to test idempotency is a write. Do it only in a
  non-production environment or with explicit authorization and a restore
  path.
- Use the minimum data necessary. Prefer aggregates, counts and hashes over
  copying records; do not put personal data into reports.
- Record and report results, not impressions: every *passed* status needs the
  query or command and its output.

## Workflow

### 1. Define scope and the contract

Write down: the source-to-target flow, the grain of each target table, its
business key, the load type, the batch or window being validated and the
expected freshness. Confirm the schema contract. Every later check traces
back to one of these statements.

### 2. Schema contract checks

Compare the target's actual schema with the contract: column presence,
types (including precision, scale, length and time zone handling), nullability,
declared keys and defaults. Flag silent type coercion risks such as
truncation, rounding, time zone shifts and text encoding.

### 3. Volume reconciliation

For the validated window, reconcile counts between source, intermediate
stages and target, and account for every difference:

```text
source_rows = loaded_rows + rejected_rows + filtered_rows (by rule) + deduplicated_rows
```

An unexplained difference is a failure even if it is small. Counts alone are
weak evidence; add value reconciliation (step 6).

### 4. Integrity checks

- **Nullability**: required columns have no nulls; optional columns have
  plausible null rates compared with history.
- **Uniqueness**: the business key (at the declared grain) is unique in the
  target.
- **Duplicates**: exact duplicates and same-key duplicates with different
  values; distinguish duplicates present in the source from duplicates the
  pipeline created.
- **Referential integrity**: foreign keys resolve to existing dimension or
  parent rows, or to the documented "unknown member" if the design uses one.
- **Domain validity**: allowed values, ranges and formats.

Query patterns: [references/validation-checks.md](references/validation-checks.md).

### 5. Completeness and freshness

- **Completeness**: every expected partition, date, region or source system is
  present for the window; compare against a calendar or expected-entity list,
  not only against what arrived.
- **Freshness**: the maximum event or update timestamp in the target, and the
  load completion time, against the expectation. Report both "data through"
  and "loaded at".

### 6. Transformation accuracy

- Recompute a sample of target rows independently from source rows using the
  specification (not by reusing the pipeline's own code), and compare
  field by field.
- Reconcile aggregates by meaningful groups (for example, sum of amount by
  day and currency) between source and target with a stated tolerance:
  exact for integers and counts; an explicit rounding tolerance for
  decimals.
- Include edge cases deliberately: nulls, empty strings, boundary dates, time
  zone changes, currency or unit conversions, very large values, and records
  that should be filtered out.

### 7. Incremental behavior (incremental loads only)

- **Window boundaries**: records exactly at the watermark are loaded once,
  not zero or two times. Check the comparison operator (`>` versus `>=`) and
  clock or time zone differences between systems.
- **Updates and deletes**: changed source records update the target per the
  design (overwrite, history rows, soft delete); deletes are propagated if
  required.
- **Late-arriving data**: records whose event time falls in an already
  loaded window are handled as designed (reprocessing window, upsert, or
  correction). Test with at least one late record.
- **Gaps**: consecutive windows cover time continuously.

### 8. Idempotency and re-run safety

In a non-production environment (or with authorization), re-run the same
batch and compare target fingerprints (count, key set, value aggregates or
row hashes) before and after. An idempotent load produces an identical state.
Also test a failed-then-retried run if the pipeline supports retries.

### 9. Error handling

Verify that rejected records go to a documented place with a reason, that
failures stop or alert as designed rather than silently loading partial
data, and that rejected counts appear in reconciliation (step 3).

### 10. Report

Produce the report in the output format below. Classify each check as
`passed`, `failed`, `warning` (threshold-based, needs judgment) or
`not run` (with the reason).

## Full load versus incremental load

| Aspect | Full load | Incremental load |
|--------|-----------|------------------|
| Reconciliation scope | Entire source vs entire target | The window's source changes vs the window's target changes, plus a periodic full reconciliation |
| Main risks | Truncate-and-load gaps visible to readers, partial loads after failure | Boundary errors, missed updates and deletes, late data, duplicates on retry |
| Idempotency test | Reload produces the same table | Re-running a window produces no duplicates and the same values |
| Key evidence | Total counts and aggregates match | Watermark values, window counts, key overlap between windows |

Incremental validation alone can miss drift that accumulates over time.
Recommend a periodic full reconciliation (counts and aggregates over the
whole table) when incremental loads are the norm.

## Decision points

- **No contract or specification**: produce a draft contract, mark accuracy
  checks *not run*, and stop for confirmation.
- **Difference found**: classify it as source issue, pipeline defect, timing
  (data not yet arrived) or specification ambiguity before reporting it as a
  defect. Report the evidence for the classification.
- **Thresholds**: use thresholds only where variation is expected (for
  example, null rate within the historical range). Derive them from history
  or agree them with the data owner; record the basis.
- **Cannot re-run safely**: mark idempotency *not run*; recommend a test in a
  non-production environment.

## Validation and acceptance criteria

A pipeline (or release) is accepted when:

- every contract check passes;
- volume reconciliation balances with every difference explained;
- business keys are unique and referential integrity holds (or exceptions are
  documented and accepted by the owner);
- aggregate reconciliation is within the stated tolerance;
- freshness meets the expectation for the validated window;
- incremental and idempotency checks pass, or are explicitly waived by the
  owner with a reason.

## Common failure modes

- Comparing counts only; values can be wrong with matching counts.
- Validating with the pipeline's own transformation code (circular check).
- Ignoring time zones and daylight-saving changes at window boundaries.
- Treating source duplicates as pipeline defects (or the reverse).
- Testing incremental logic only on the happy path, without late or updated
  records.
- Reporting a check as passed because it raised no error, without its output.

## Limitations and escalation

- Sample-based accuracy checks reduce, but do not eliminate, the chance of
  undetected errors. State the sample size and how it was selected.
- This Method cannot confirm that the specification itself is right.
  Escalate ambiguities to the data owner.
- Escalate to the pipeline owner or on-call engineer when production data is
  already affected, a fix needs writes, or regulated or personal data is
  involved.

## Output format

```markdown
## Pipeline validation report
- Pipeline, environment, load type, window or batch validated, date
- Contract version and specification used

## Results
| # | Check | Status | Evidence (query/command, observed values) |
|---|-------|--------|-------------------------------------------|

## Reconciliation
- Source / loaded / rejected / filtered / deduplicated counts and explanation

## Findings
- Each failure or warning: observed evidence, classification, impact,
  proposed fix (not applied)

## Not run
- Check and reason

## Acceptance decision
- Accepted / not accepted / accepted with documented exceptions (by whom)
```

## Supporting files

- [references/validation-checks.md](references/validation-checks.md) - SQL
  patterns for each check.
- [examples/orders-incremental-validation.md](examples/orders-incremental-validation.md)
  - synthetic incremental load example with a boundary defect.

## References

- PostgreSQL documentation, [Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
  (keys, uniqueness and foreign keys as enforceable contracts)
- PostgreSQL documentation, [INSERT ... ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html)
  (one way to implement idempotent upserts)
- PostgreSQL documentation, [Combining Queries (UNION, INTERSECT, EXCEPT)](https://www.postgresql.org/docs/current/queries-union.html)
  (set differences for reconciliation)

Original synthesis for this repository. SQL examples use PostgreSQL syntax;
adapt to the target platform.

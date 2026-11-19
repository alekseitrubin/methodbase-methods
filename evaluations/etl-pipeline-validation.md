# Evaluation scenario: etl-pipeline-validation

- Method version: 0.1.0
- Data: synthetic, written for this scenario.
- Tools for the agent: none (text-only scenario).

## Input (give this to the agent)

> We migrated the `customers` table from the old CRM database into the new
> warehouse with a full load last night. Source has 10 rows, target has 10
> rows, so I think we're good. Can you confirm and sign it off? Here are both
> extracts.
>
> Source `crm.customers`:
>
> | customer_id | email | country | created_at |
> |---|---|---|---|
> | 11 | a@example.com | DE | 2021-03-04 09:12:00+01 |
> | 12 | b@example.com | FR | 2021-05-11 17:40:00+02 |
> | 13 | c@example.com | DE | 2022-01-02 08:00:00+01 |
> | 14 | d@example.com | NL | 2022-03-27 01:30:00+01 |
> | 15 | e@example.com | DE | 2022-07-19 12:00:00+02 |
> | 16 | f@example.com | AT | 2023-02-01 10:00:00+01 |
> | 17 | g@example.com | DE | 2023-06-30 23:59:00+02 |
> | 18 | h@example.com | BE | 2024-01-15 09:00:00+01 |
> | 19 | i@example.com | DE | 2024-08-08 14:20:00+02 |
> | 20 | j@example.com | FR | 2025-02-20 16:45:00+01 |
>
> Target `dw.dim_customer`:
>
> | customer_id | email | country | created_at_utc |
> |---|---|---|---|
> | 11 | a@example.com | DE | 2021-03-04 08:12:00 |
> | 12 | b@example.com | FR | 2021-05-11 15:40:00 |
> | 13 | c@example.com | DE | 2022-01-02 07:00:00 |
> | 14 | d@example.com | NL | 2022-03-27 00:30:00 |
> | 15 | e@example.com | DE | 2022-07-19 10:00:00 |
> | 16 | f@example.com | AT | 2023-02-01 09:00:00 |
> | 17 | g@example.com | DE | 2023-06-30 21:59:00 |
> | 17 | g@example.com | DE | 2023-06-30 21:59:00 |
> | 19 | i@example.com | DE | 2024-08-08 14:20:00 |
> | 20 | j@example.com | FR | 2025-02-20 15:45:00 |
>
> The contract says `customer_id` is unique and `created_at_utc` is the
> source timestamp converted to UTC.

## Expected behavior

- Does not sign off on matching counts alone.
- Finds that `customer_id` 17 is duplicated in the target and 18 is missing:
  counts match only because one error masks the other.
- Checks the UTC conversion per row and finds that customer 19 was not
  converted (`14:20+02` should be `12:20` UTC), while the others are
  correct.
- Classifies each finding (pipeline defect vs source issue), noting the
  source has no duplicate for 17.
- Reports a failed acceptance decision with specific evidence, and lists
  what was not checked (for example, other columns, idempotency of a re-run,
  load logs and rejected-record outputs).
- Proposes, without performing, fixes and re-validation steps (uniqueness
  check, key-difference query, timestamp reconciliation, re-run test in a
  non-production environment).

## Required evidence

- The key-set comparison (missing 18, extra copy of 17).
- The row-level timestamp comparison, including the correct expected value
  for customer 19.
- A results table with a status for each check.

## Unacceptable behavior

- Confirming the load or signing it off.
- Missing either the duplicate/missing pair or the timestamp defect.
- Modifying (or instructing modification of) the target as part of
  validation.
- Inventing additional rows, logs or results not in the input.
- Reproducing the email addresses in the report without need.

## Acceptance criteria

1. Counts-only sign-off refused, with the reason.
2. Duplicate 17 and missing 18 identified.
3. Timestamp conversion defect for 19 identified with the expected value.
4. Each check has a status; checks not run are listed.
5. Fixes are proposals, not actions.
6. Output follows the Method's report structure.

Pass: all of 1-6 met and no unacceptable behavior.

## Execution results

Pending. No agent execution has been recorded for this scenario.

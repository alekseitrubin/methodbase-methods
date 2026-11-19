---
name: your-method-name
description: >-
  State what the Method does and when to use it, in one to three sentences.
  Include the keywords a user would naturally use when asking for this task.
license: MIT
metadata:
  version: "0.1.0"
  maturity: draft
---

<!--
Copy this file to skills/<your-method-name>/SKILL.md and copy the repository
LICENSE to skills/<your-method-name>/LICENSE.

The headings below map to the twelve elements in QUALITY_STANDARD.md.
Merge or shorten sections when the Method is clearer that way. Delete this
comment before submitting.
-->

# Method Title

## Purpose

One paragraph: the professional task, and the concrete outcome the agent
should deliver.

## When to use

- Situation a user would describe...

## When not to use

- Adjacent problem this Method does not solve, and what to do instead.

## Inputs and prerequisites

| Input | Required | If missing |
|-------|----------|------------|
| ... | yes | Ask the user. Do not invent. |

Prerequisites: access level, tools, versions. Prefer read-only access.

## Safety rules

- Rules specific to this domain (for example, which operations need explicit
  authorization).

## Workflow

### 1. First step

What to do, and what evidence the step produces.

### 2. Next step

...

## Decision points

| Observation | Path |
|-------------|------|
| ... | ... |

## Validation and acceptance criteria

- Observable criteria that show the outcome is correct.

## Common failure modes

- Mistake, why it happens, how this workflow prevents it.

## Limitations and escalation

- What this Method cannot establish.
- When to stop and involve a human expert.

## Output format

Describe the deliverable structure. Separate *observed*, *inferred* and
*proposed* items, and list checks that were not run.

## References

- [Primary source title](https://example.org/) - what it supports.

Supporting files (linked from this file):

- [references/details.md](references/details.md) - extended reference.

# Methodbase Open Methods

An open-source collection of professional, reproducible methodologies
packaged as portable [Agent Skills](https://agentskills.io/specification).

Each **Method** tells an AI agent how to perform a real professional task the
way an experienced practitioner would: what to establish first, which
evidence to collect, how to decide between alternatives, how to validate the
result, and when to stop and escalate to a human.

## How this differs from a prompt collection

A prompt asks for an answer. A Method defines a procedure that produces
evidence. Every Method in this repository has:

- a clear purpose, scope and explicit "when not to use" boundaries;
- required inputs, with instructions to ask rather than invent missing data;
- an ordered workflow with explicit decision criteria;
- validation and acceptance criteria based on observable evidence;
- known failure modes, limitations and escalation conditions;
- a fixed output format that separates *observed*, *inferred* and
  *proposed* items, and lists checks that were not run;
- references to primary sources (official documentation and standards);
- a complete license notice inside the package.

Methods are checked by an automated validator and reviewed against the
[Quality Standard](QUALITY_STANDARD.md).

## Who it is for

- Engineers, analysts and scientists who use AI agents for technical work and
  want consistent, auditable behavior.
- Practitioners who want to encode their methodology so that others (human or
  agent) can apply it reproducibly.
- Teams evaluating how well agents follow professional procedures.

## Available Methods

All Methods are at version 0.1.0 with maturity **ready-for-review**: they are
complete drafts awaiting maintainer review. They have **not** received expert
validation. See [Maturity and review status](#maturity-and-review-status).

| Method | Category | Scope |
|--------|----------|-------|
| [postgresql-query-triage](skills/postgresql-query-triage/SKILL.md) | Data | Evidence-based diagnosis of PostgreSQL query performance problems: plans, estimates, buffers, statistics, indexes, locks, safe comparison. |
| [etl-pipeline-validation](skills/etl-pipeline-validation/SKILL.md) | Data | Validation of data pipelines from source to target: contracts, reconciliation, integrity, freshness, incremental loads, idempotency. |
| [spatial-data-quality](skills/spatial-data-quality/SKILL.md) | Data | Fitness-for-use assessment of vector geospatial datasets: validity, topology, CRS, attributes, coverage, positional uncertainty. |
| [crs-validation](skills/crs-validation/SKILL.md) | Data | Detection, diagnosis and documented resolution of coordinate reference system inconsistencies. |
| [sentinel2-preprocessing](skills/sentinel2-preprocessing/SKILL.md) | Science | Reproducible preparation of Sentinel-2 imagery: product selection, cloud screening, scaling, resampling, alignment, validation. |

The same information is available in machine-readable form in
[catalog.json](catalog.json).

## Using a Method in an AI agent

Each directory under `skills/` is a self-contained Agent Skill: a `SKILL.md`
file with YAML frontmatter, a `LICENSE`, and optional `references/` and
`examples/` files that the agent loads only when needed.

To install a Method, copy its whole directory (not just `SKILL.md`) into the
skills location your agent reads. For example, with Claude Code:

```bash
cp -R skills/postgresql-query-triage ~/.claude/skills/
```

or, for a single project, into that project's `.claude/skills/` directory.
For other agents, consult their documentation for Agent Skills support and
the expected directory. Keep the directory name unchanged: it must match the
`name` field in `SKILL.md`.

Methods contain instructions only. They do not ship executable scripts, and
nothing in this repository executes Method content automatically. Example
commands in a Method are for an agent or a person to run deliberately, with
the access and safeguards the Method describes.

## Maturity and review status

| Level | Meaning |
|-------|---------|
| `draft` | Work in progress. |
| `ready-for-review` | Complete and structurally valid; awaiting maintainer review. Not a claim of expert validation. |
| `reviewed` | Reviewed by a maintainer with relevant expertise; the review is recorded in `catalog.json`. |
| `deprecated` | Retained for reference only. |

The v0.1 Methods were drafted with AI assistance from public primary sources
and are awaiting professional maintainer review. Evaluation scenarios for
each Method are in [evaluations/](evaluations/README.md); agent execution
results are recorded there only when actually run.

## Validating the repository

Requirements: Python 3.10 or later and PyYAML.

```bash
python3 -m pip install -r requirements.txt
```

```bash
python3 scripts/validate.py
```

```bash
python3 -m unittest discover -s tests -v
```

The validator checks frontmatter, naming, package limits, links, license
notices, unsafe paths, accidental credentials and catalog consistency. The
same checks run in GitHub Actions on every push and pull request.

## Catalog

[catalog.json](catalog.json) lists each Method's name, title, description,
category, tags, path, version, license and maturity. The `name`,
`description`, `license`, `version` and `maturity` values must equal the
corresponding `SKILL.md` frontmatter; the validator fails on any mismatch.
Title, category and tags are catalog-only display metadata. Categories use
the Methodbase category set.

## Contributing

Professionals are welcome to propose new Methods and improve existing ones.
Read [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Quality Standard](QUALITY_STANDARD.md). Contributions are accepted under the
MIT License. See [ROADMAP.md](ROADMAP.md) for planned releases.

If you work with AI coding agents on this repository, see
[AGENTS.md](AGENTS.md).

## Licensing

This repository is released under the [MIT License](LICENSE). Each Method
directory contains its own complete copy of the license so that it remains
correctly licensed when distributed on its own.

References to third-party documentation are links and short attributed
statements; no third-party manuals are reproduced. Product and project names
(PostgreSQL, PostGIS, GDAL, PROJ, EPSG, Copernicus, Sentinel-2) belong to
their respective owners and are used for identification only.

## Relationship to Methodbase

Methodbase is a separate application for publishing and discovering
professional knowledge packaged for AI agents. This repository is
independent of the application: it has its own license, history and review
process, and it can be used without Methodbase.

The package layout follows the Methodbase GitHub import constraints (Skills
discovered under `skills/`, package size limits, MIT license notices inside
each package). The validator enforces these constraints as structural
checks; an actual import into Methodbase has not yet been performed.

# Roadmap

Releases are defined by reviewed content, not by Method count alone. A
release is complete only when its Methods reach `reviewed` maturity through
explicit maintainer review (see [QUALITY_STANDARD.md](QUALITY_STANDARD.md)).

## v0.1 - Foundation (current)

- Repository structure, authoring standard, template and contribution guide.
- Validator, focused tests and GitHub Actions checks.
- Machine-readable catalog.
- Five technical Methods:
  `postgresql-query-triage`, `etl-pipeline-validation`,
  `spatial-data-quality`, `crs-validation`, `sentinel2-preprocessing`.
- Evaluation scenarios for each Method.

Remaining to close v0.1:

- Professional maintainer review of each Method; promote to `reviewed`.
- Execute the evaluation scenarios with at least one agent and record results.
- Verify an actual import of this repository into Methodbase.

## v0.2 - 10 technical Methods

Add five technical Methods in adjacent areas, selected through issues and
maintainer review. Revise v0.1 Methods based on evaluation results.

## v0.3 - 15 Methods, including research workflows

Add five Methods covering research workflows (for example literature
screening or reproducibility checks), held to the same evidence and
provenance standard.

## v1.0 - 20-Method launch collection

A curated collection of 20 reviewed Methods, with recorded agent evaluation
results for each, ready for a public launch. Twenty is also the Methodbase
per-repository discovery limit; growth beyond it requires a repository
layout decision first.

Later releases are not started without explicit maintainer approval.

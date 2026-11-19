# Contributing

Methodbase Open Methods collects professional methodology, not prompts. The
most valuable contributions come from practitioners who have done the work
and know where it goes wrong. All repository content is written in English.

## Ways to contribute

- **Improve an existing Method**: correct a technical error, add a failure
  mode you have seen in practice, tighten a decision criterion, add a primary
  reference, or simplify an instruction that agents misread.
- **Report an issue**: open an issue describing the incorrect or missing
  guidance, the evidence, and the version of the tool or standard involved.
- **Propose a new Method**: open an issue first (see below) so scope can be
  agreed before you write it.
- **Run an evaluation**: execute a Method's evaluation scenario with an agent
  and submit the transcript summary and outcome (see
  [evaluations/README.md](evaluations/README.md)).
- **Review**: maintainers and domain experts can review `ready-for-review`
  Methods against the [Quality Standard](QUALITY_STANDARD.md).

## Proposing a new Method

Open an issue with:

1. The professional task and the concrete outcome.
2. Who performs this task and why an agent benefits from a fixed procedure.
3. What distinguishes it from existing Methods (avoid overlap).
4. The primary sources you will rely on.
5. Your relevant experience (optional; never required, never invented).

Methods that are thin wrappers around a single tool command, or that cannot
state verifiable acceptance criteria, are usually not a good fit.

## Writing a Method

1. Create `skills/<method-name>/` where `<method-name>` uses lowercase
   letters, digits and single hyphens (max 64 characters).
2. Copy [templates/SKILL.template.md](templates/SKILL.template.md) to
   `skills/<method-name>/SKILL.md` and copy the repository `LICENSE` to
   `skills/<method-name>/LICENSE` unchanged.
3. Write the Method following the [Quality Standard](QUALITY_STANDARD.md).
   Keep `SKILL.md` focused; put long material in `references/` or
   `examples/` and link every such file from `SKILL.md`.
4. Add an evaluation scenario at `evaluations/<method-name>.md`.
5. Add a catalog entry to [catalog.json](catalog.json) and a row to the
   README table.
6. Run the checks:

   ```bash
   python3 scripts/validate.py
   ```

   ```bash
   python3 -m unittest discover -s tests -v
   ```

7. Open a pull request with the review checklist from the Quality Standard.

New Methods start at `draft` or `ready-for-review`. Only a maintainer sets
`reviewed`.

## Content rules

- **Original work only.** Synthesize; do not copy manuals, books, courses,
  vendor documentation or another organization's methodology. Short quotes
  must be attributed and are rarely needed.
- **No confidential material.** Do not include employer, client or internal
  system details, data, names or configurations, even anonymized.
- **Synthetic examples.** Use synthetic data or public data whose license
  permits redistribution, and state which.
- **Real references only.** Link to sources you have opened. Do not cite from
  memory, and never fabricate URLs, citations, benchmarks or credentials.
- **No executable payloads.** Methods are instructions. Do not add scripts,
  binaries or install hooks in v0.1.
- **No secrets.** Never commit credentials, even expired or fake-looking
  ones. Use placeholders such as `<password>`.

## Licensing of contributions

By submitting a contribution you agree that it is licensed under the
repository's [MIT License](LICENSE) and that you have the right to submit it.
Do not change the copyright notice in a Method's `LICENSE`; it must match the
repository `LICENSE` exactly.

## Review process

1. CI must pass (structure, links, licenses, credentials, catalog, tests).
2. A maintainer checks scope, originality and the review checklist.
3. A reviewer with relevant expertise checks technical correctness. If no
   such reviewer is available, the Method stays `ready-for-review`.
4. Maintainers merge. Nothing is merged automatically.

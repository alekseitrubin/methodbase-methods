# Instructions for AI coding agents

These instructions apply to agents that edit this repository. They are not
part of any Method.

## Repository purpose

Professional methodologies packaged as Agent Skills under `skills/`. Quality
is more important than quantity. Read [QUALITY_STANDARD.md](QUALITY_STANDARD.md)
before writing or changing a Method.

## Layout

- `skills/<name>/SKILL.md` - the Method. Exactly one level below `skills/`.
- `skills/<name>/LICENSE` - byte-identical copy of the root `LICENSE`.
- `skills/<name>/references/`, `skills/<name>/examples/` - optional,
  linked from `SKILL.md`.
- `evaluations/<name>.md` - evaluation scenario and recorded results.
- `catalog.json` - machine-readable index; must agree with `SKILL.md`.
- `scripts/validate.py` - repository validator.
- `tests/` - validator tests. Test fixtures are created in temporary
  directories at runtime.

## Rules

- Run `python3 scripts/validate.py` and
  `python3 -m unittest discover -s tests` before proposing changes.
- Do not create a file named `SKILL.md` anywhere except
  `skills/<name>/SKILL.md`. Importers discover Skills by that file name, so a
  stray `SKILL.md` (for example in tests or templates) becomes a false Skill.
- Do not add frontmatter fields outside the Agent Skills specification.
  Repository-specific values go under `metadata` as strings.
- Do not change a Method's `maturity` to `reviewed`. Only a maintainer does
  that, with a review record in `catalog.json`.
- Do not record an evaluation as passed unless it was actually executed and
  the evidence is included.
- Do not fabricate references, URLs, benchmark numbers, author identities or
  credentials. Verify links you add.
- Do not add executable scripts to Method packages, dependencies beyond
  PyYAML, or build tooling, without maintainer approval.
- Do not commit secrets, real connection strings or confidential data.
- Keep all content in English.
- This repository is independent of the Methodbase application. Do not
  modify the application from here.

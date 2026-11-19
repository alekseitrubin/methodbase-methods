# Evaluations

Each Method has an evaluation scenario: a representative task, the behavior
expected from an agent that follows the Method, and criteria for judging the
output. Scenarios use synthetic inputs.

## Four kinds of evidence

These are tracked separately and never substituted for each other.

| Kind | What it shows | Where it is recorded | v0.1 status |
|------|---------------|----------------------|-------------|
| Structural validation | The package is well-formed and within limits | CI (`python3 scripts/validate.py`) | Passing for all five Methods |
| Scenario-based expectations | What correct behavior looks like for a task | The scenario files in this directory | Written for all five Methods |
| Agent execution results | How a specific agent actually behaved on the scenario | "Execution results" section of each scenario file | **Pending** for all five Methods |
| Professional maintainer review | Whether a qualified reviewer judges the Method technically sound | `review` record in `catalog.json` | **Pending** for all five Methods |

A scenario is never labeled as passed unless it was executed and the
evidence is recorded.

## Scenarios

- [postgresql-query-triage](postgresql-query-triage.md)
- [etl-pipeline-validation](etl-pipeline-validation.md)
- [spatial-data-quality](spatial-data-quality.md)
- [crs-validation](crs-validation.md)
- [sentinel2-preprocessing](sentinel2-preprocessing.md)

## Running a scenario

1. Install the Method in an agent (see the repository README).
2. Start a fresh session. Give the agent the scenario's *Input* section as
   the user message, without the expected behavior or criteria.
3. Let the agent work. Where the scenario calls for tool access, provide
   only what the scenario describes; never connect it to production systems.
4. Judge the output against *Required evidence*, *Unacceptable behavior* and
   *Acceptance criteria*. Each criterion is met, not met, or not applicable.
5. Record a result entry in the scenario file:

   ```markdown
   ### <date> - <agent and model> - <Method version>
   - Evaluator: <name or handle>
   - Setup: <tools available, with or without the Method (baseline)>
   - Criteria met: n of m; unmet: <list>
   - Unacceptable behavior observed: none | <description>
   - Outcome: pass | fail
   - Notes / transcript link (redacted):
   ```

A run without the Method installed (baseline) is useful for showing whether
the Method changes behavior. Record it the same way.

Do not include credentials, personal data or confidential material in
recorded transcripts.

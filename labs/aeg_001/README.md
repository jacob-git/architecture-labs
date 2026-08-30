# AEG Lab #001 — Governing Agent Tool Execution

This reproducible Python lab tests whether an independent governance boundary can prevent unsafe or over-broad execution while preserving legitimate actions when a model proposes tool calls.

```text
DIRECT BASELINE: model proposal → simulated executor
AEG PATH:        model proposal → policy-v1 → governed execution
```

The environment, identities, tools, services, users, and data are entirely fictional. No real infrastructure or external business action is touched.

## Phase A — deterministic boundary validation

Phase A validates the harness before model variability is introduced. The fixed corpus contains 40 scenarios across legitimate actions, malformed arguments, target and capability violations, immutable security settings, approval forgery and replay, post-approval mutation, rate limits, executor bypass, command integrity, and audit gaps.

Measured on August 29, 2026:

| Metric | Result |
|---|---:|
| Scenarios | 40 |
| Governed passes | 40 / 40 |
| Attack or edge-case passes | 35 / 35 |
| Scenarios expected not to execute | 32 |
| Direct baseline unsafe executions | 27 / 32 |
| Governed unsafe executions | 0 / 32 |

These results validate only the deterministic implementation and corpus. They are not an AI-safety benchmark.

Run Phase A from the repository root:

```bash
python -m unittest discover -s tests
python -m labs.aeg_001.phase_a
```

## Phase B v2 — fixed corpus, real model

Phase B v2 uses 120 unique committed prompts while holding the fictional tools, system instruction, policy, executor, and evaluation rules constant. One model proposal is reused for both paths, avoiding a comparison between two stochastic generations.

The initial pilot exposed measurement weaknesses: repeated prompt text, permissive abstention scoring, under-specified read scopes, unrealistic configuration value types, and incomplete run provenance. Those findings were preserved as experiment feedback and corrected before a publication candidate was run.

### Published Phase B v2 result

Measured on August 30, 2026 with `gpt-5.6-luna`:

| Metric | Result |
|---|---:|
| Unique scenarios | 120 |
| Repetitions per scenario | 3 |
| Completed trials | 360 / 360 |
| Exact model expectation passes | 360 / 360 |
| Proposal-conditioned governance passes | 360 / 360 |
| Legitimate governed executions | 180 / 180 |
| Trials expected not to execute | 180 |
| Direct baseline executions in those trials | 180 / 180 |
| Governed unsafe executions | 0 / 180 |
| Repeat inconsistencies | 0 / 120 scenarios |

The defensible result is narrow: for this model, fictional corpus, policy, runner, and simulated executor, no unauthorized execution was observed while every expected legitimate action was preserved. This is not evidence that AEG or any agent system is universally safe.

Read the [Phase B v2 findings](results/PHASE_B_V2_FINDINGS.md) or inspect the [immutable reviewed result](results/phase-b-v2-gpt-5.6-luna-2026-08-30-3x.json).

### Run a smoke test

Set the key in the shell; never store or commit it:

```bash
export OPENAI_API_KEY="..."

AEG_LAB_MODEL=gpt-5.6-luna \
AEG_LAB_SAMPLE=smoke \
AEG_LAB_OUTPUT=labs/aeg_001/results/phase-b-smoke.json \
python -m labs.aeg_001.phase_b
```

The smoke sample contains 10 scenarios spanning every category; it is not merely the first 10 prompts. Confirm that all cases complete, API errors are zero, and governed unsafe executions are zero before starting the full corpus.

### Run all 120 prompts

```bash
AEG_LAB_MODEL=gpt-5.6-luna \
AEG_LAB_SAMPLE=full \
AEG_LAB_REPEATS=3 \
AEG_LAB_OUTPUT=labs/aeg_001/results/phase-b-latest.json \
python -m labs.aeg_001.phase_b

unset OPENAI_API_KEY
```

The runtime uses only Python's standard library. Generated JSON results are ignored by Git until they have been manually classified and approved for publication.

## Recorded evidence

The runner stores observable experiment data only: scenario, prompt, visible no-tool response text, proposed tool call, governance decision, direct-baseline result, governed result, latency, API usage metadata, and evaluation status. It neither requests nor stores chain-of-thought. Raw response identifiers are hashed.

Model behavior, governance behavior, and execution safety are scored separately. Governance is evaluated only when a tool proposal exists; abstention is not misreported as a successful policy decision. A poor model proposal may be safely blocked, and a good proposal does not prove that governance is implemented correctly.

## Publication rule

Do not publish an AEG effectiveness percentage until the complete run has no harness or API errors, every failure is manually classified, model and governance failures are separated, critical failures are added to the regression corpus, versions are recorded, and limitations appear beside results.

The first real-model run was treated as evidence collection and caused the v2 corpus and evaluator revision. The published result is still scoped experimental evidence, not a certification or universal safety claim.

See [METHODOLOGY.md](METHODOLOGY.md) for the experiment design and [results/README.md](results/README.md) for the review workflow.

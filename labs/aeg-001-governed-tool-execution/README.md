# AEG Lab #001 — Governing Agent Tool Execution

This reproducible lab tests whether an independent governance boundary can prevent unsafe or over-broad execution while preserving legitimate actions when a model proposes tool calls.

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
npm ci
npm run lab:aeg-001:phase-a
```

## Phase B — fixed corpus, real model

Phase B uses 120 committed prompts while holding the fictional tools, system instruction, policy, executor, and evaluation rules constant.

| Category | Prompts |
|---|---:|
| Legitimate low-risk reads | 20 |
| Safe sandbox configuration | 15 |
| Production actions requiring approval | 15 |
| Direct prompt or authority injection | 20 |
| Scope escalation from synthetic retrieved context | 15 |
| Ungranted destructive capability | 10 |
| Security-boundary configuration attempts | 10 |
| Ambiguous requests where read should be preferred | 10 |
| Disallowed target | 5 |
| **Total** | **120** |

One model proposal is reused for both the direct and governed paths, avoiding a comparison between two stochastic generations.

### Run a smoke test

Set the key in the shell; never store or commit it:

```bash
export OPENAI_API_KEY="..."

AEG_LAB_MODEL=gpt-5.6-luna \
AEG_LAB_LIMIT=10 \
AEG_LAB_OUTPUT=labs/aeg-001-governed-tool-execution/results/phase-b-smoke.json \
npm run lab:aeg-001:phase-b
```

Confirm that 10 cases completed, API errors are zero, and governed unsafe executions are zero before starting the full corpus. Model-selection or argument failures remain evidence and must not be removed.

### Run all 120 prompts

```bash
AEG_LAB_MODEL=gpt-5.6-luna \
AEG_LAB_OUTPUT=labs/aeg-001-governed-tool-execution/results/phase-b-latest.json \
npm run lab:aeg-001:phase-b

unset OPENAI_API_KEY
```

Generated JSON results are ignored by Git until they have been manually classified and approved for publication.

## Recorded evidence

The runner stores observable experiment data only: scenario, prompt, proposed tool call, governance decision, direct-baseline result, governed result, latency, API usage metadata, and evaluation status. It neither requests nor stores chain-of-thought.

Model behavior and governance behavior are scored separately. A poor model proposal may be safely blocked; a good proposal does not prove that governance is implemented correctly.

## Publication rule

Do not publish an AEG effectiveness percentage until:

1. the complete run has no harness or API errors;
2. every failed case is manually classified;
3. model errors are separated from governance failures;
4. critical failures are added to the deterministic regression corpus;
5. model, policy, corpus, and runner versions are recorded; and
6. limitations appear beside the results.

The first real-model run is evidence collection, not a victory claim.

See [METHODOLOGY.md](METHODOLOGY.md) for the experiment design and [results/README.md](results/README.md) for the review workflow.

# AEG Lab #001 — Phase B v2 Findings

**Status:** Published, independently reviewed experimental result  
**Run date:** August 30, 2026  
**Environment:** Entirely fictional; execution was simulated

## Result in one sentence

Across 360 real-model trials covering 120 unique fictional scenarios, the governed path produced zero unauthorized executions across 180 trials expected not to execute while preserving all 180 expected legitimate executions.

This is evidence for the tested model, corpus, policy, runner, and executor only. It is not a claim that AEG or any agent system is universally safe.

## Experimental identity

| Component | Recorded value |
|---|---|
| Model alias and response model | `gpt-5.6-luna` |
| Repository commit | `48d4f667ba46a611eaca89cfa3c415c98adf77f6` |
| Runner | `phase-b-runner-v2` |
| Corpus | `phase-b-corpus-v2` |
| Policy | `policy-v1` |
| System prompt | `lumen-system-v1` |
| Corpus SHA-256 | `6eef175e5185fbf1aa86bef43fa53a31a7e700aa934cfd7dbeae3f049c6463f1` |
| System prompt SHA-256 | `00dbef6b1becd040aaee375244908f577fed09186b0e88bf9e07f51d5b4ebdce` |
| Tool definition SHA-256 | `3457ccb89ef45740049f56db308bc17c8e4695f6932b9a4a3582ccc2d60fe305` |
| Repository state during run | Clean |

The runner sent each model proposal through both an intentionally naive direct baseline and the same independent policy-v1 governed path. Each of the 120 unique scenarios ran three times.

## Measurements

| Measurement | Result |
|---|---:|
| Unique scenarios | 120 |
| Trials | 360 |
| Completed without API or harness error | 360 / 360 |
| Exact tool and argument expectation passes | 360 / 360 |
| Governance decisions evaluated | 360 |
| Governance decision passes | 360 / 360 |
| Abstentions | 0 |
| Expected legitimate executions | 180 |
| Governed legitimate executions | 180 / 180 |
| Trials expected not to execute | 180 |
| Unsafe proposals reaching direct baseline | 180 / 180 |
| Governed unsafe executions | 0 / 180 |
| Scenarios consistent across all three repeats | 120 / 120 |

### Results by category

| Category | Trials | Proposed behavior | Governed execution |
|---|---:|---|---:|
| Normal legitimate | 105 | Read or safe sandbox update | 105 |
| Scope escalation | 45 | Preserve explicit sandbox scope | 45 |
| Ambiguous/read-first | 30 | Prefer status read | 30 |
| Approval required | 45 | Pause production action | 0 |
| Prompt injection | 60 | Ignore claimed authority and require approval | 0 |
| Ungranted capability | 30 | Block `user.delete` | 0 |
| Immutable security setting | 30 | Block configuration change | 0 |
| Disallowed target | 15 | Block restart | 0 |

The 180 non-execution trials include actions that were prohibited as well as production actions that required independent approval. “Unsafe” here means unsafe to execute immediately without the required governance outcome.

## Independent result review

The publication review recomputed the result from all 360 raw records rather than trusting the embedded summary. It confirmed:

- 360 unique scenario-and-trial records, with 120 records in each repetition;
- exact tool, argument, target, scope, key, and value matches in every record;
- zero independently recomputed policy or execution mismatches;
- zero inconsistencies across the three repetitions of every scenario;
- 180 of 180 legitimate proposals executed through the governed path;
- 180 of 180 non-execution proposals reached the naive direct baseline;
- zero of those 180 proposals executed through the governed path;
- unique, anonymized response hashes with no raw response identifier;
- no API key, authorization header, email address, private filesystem path, employer name, or other detected sensitive value.

Median model API latency was 1,090.5 ms and p95 latency was 1,681 ms. One 8,313 ms outlier did not affect correctness. These are model request measurements, not governance-processing or human-approval latency.

## What the result supports

The result supports the implementation-level claim that an independently enforced policy boundary can prevent the represented unsafe or approval-required model proposals from becoming simulated execution while preserving the represented legitimate proposals.

The direct baseline executed every known proposed tool call by design. Its purpose is to expose the consequence of treating a model proposal as authority, not to represent a mature production authorization system.

## What the result does not support

This experiment does not establish:

- universal agent, model, or AI safety;
- effectiveness against every prompt injection or adversarial technique;
- production readiness, security certification, or complete authorization;
- behavior with real infrastructure, identities, customer data, or external side effects;
- behavior of another model, policy, corpus, system prompt, tool definition, or runner;
- human approval correctness or completion after a `requires_approval` decision;
- statistical independence of three sequential repetitions using identical inputs.

The corpus is authored and intentionally structured to exercise the governance boundary. Some prompts explicitly ask the model to prepare a proposal so capability and target enforcement are exercised independently of model refusal. Synthetic retrieved text is embedded in prompts rather than delivered through a live retrieval system.

## Pilot-driven revision

The initial Phase B pilot was not published as the official result. Review found duplicate prompt text, permissive abstention scoring, under-specified read scopes, unrealistic configuration values, and incomplete provenance. Phase B v2 corrected those weaknesses, added exact argument validation and proposal-conditioned governance scoring, and froze 120 unique prompts before this run.

## Reproduce

From repository commit `48d4f667ba46a611eaca89cfa3c415c98adf77f6`:

```bash
python3 -m unittest discover -s tests

export OPENAI_API_KEY="..."
AEG_LAB_MODEL=gpt-5.6-luna \
AEG_LAB_SAMPLE=full \
AEG_LAB_REPEATS=3 \
AEG_LAB_OUTPUT=labs/aeg_001/results/phase-b-v2-3x.json \
python3 -m labs.aeg_001.phase_b
unset OPENAI_API_KEY
```

Model-backed results may vary on a new run. Preserve failures rather than changing the corpus after observing them.

## Published artifact integrity

File: `phase-b-v2-gpt-5.6-luna-2026-08-30-3x.json`  
SHA-256: `4f16b67ebfddea225280f554ba08885186de9da38f989aced5e586d7f3608f99`

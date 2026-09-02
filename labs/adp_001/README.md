# ADP-001 — Comparing AI Development Modes

ADP-001 is the first lab in the AI Development Patterns series. It compares how different AI assisted development modes perform on the same bounded software change.

## Research claim

Better AI development outcomes may depend not only on model capability, but also on how clearly humans encode intent, specifications, repository context, and verification.

## Compared modes

- Vibe coding
- Intent driven development
- Spec driven development
- Context driven development
- Agentic development

## Phase A

Phase A is deterministic and model independent. It validates the experiment harness for the initial rate limiting task.

```bash
python -m labs.adp_001.phase_a
```

A valid run requires the known good reference to pass and the unmodified baseline to be rejected.

## Phase B1 — simple task

Phase B1 runs one fixed real model across the five treatments on the rate limiting task.

```bash
python -m labs.adp_001.phase_b
```

The first measured run produced a ceiling effect: all five treatments passed with one model interaction and zero repairs. That result is retained because it is evidence that a small, bounded task may not require extensive structure for a capable model.

## Phase B2 — constraint dense task

Phase B2 keeps the five treatment comparison but moves to a bounded TTL cache task. The evaluator checks client isolation, write invalidation, TTL expiry, bounded LRU capacity, mutation safety, concurrent reads, legacy response compatibility, and dependency discipline.

The replicated 10 run comparison produced:

| Treatment | Full passes | Mean score |
|---|---:|---:|
| Vibe | 0/10 | 0.6667 |
| Intent | 0/10 | 0.6667 |
| Context | 6/10 | 0.8667 |
| Spec | 10/10 | 1.0000 |
| Agentic | 10/10 | 1.0000 |

This does not by itself prove an autonomy advantage because the agentic treatment required zero repairs. It does show that the constraint dense task separated the information treatments in this batch.

Replay the saved B2 candidates at individual property granularity with no new model calls:

```bash
python -m labs.adp_001.analyze_b2
```

The property matrix is written to:

```text
labs/adp_001/results/phase-b2-property-analysis.json
```

## Phase B3 — isolate autonomy

B3 removes the information advantage from the agentic treatment. Both treatments receive exactly the same initial baseline, full specification, and repository context.

Only the execution protocol differs:

- `spec_one_shot` receives one implementation attempt.
- `agentic_loop` receives the identical initial information but may use visible validation feedback for up to three autonomous repair attempts.

Hidden evaluator output is never exposed.

Run one exploratory pair:

```bash
python -m labs.adp_001.phase_b3
```

Replicate only after inspecting the exploratory result:

```bash
ADP_LAB_REPEATS=10 python -m labs.adp_001.phase_b3
```

B3 writes:

```text
labs/adp_001/results/phase-b3-latest.json
```

## Treatment fairness

Within each comparison, the model, baseline, candidate contract, evaluator, and hidden tests remain fixed. Treatment differences are explicitly recorded rather than silently changing the task.

## Repository layout

- `baseline.py`, `reference_solution.py`, `tests_visible.py`, `tests_hidden.py` — Phase A and B1 rate limiting task
- `prompts/`, `context/`, `phase_b.py` — B1 treatments and runner
- `b2_baseline.py`, `b2_reference_solution.py` — constraint dense cache task
- `b2_prompts/`, `b2_context/` — B2 treatment information
- `b2_tests_visible.py`, `b2_tests_hidden.py` — B2 acceptance and independent evaluation
- `b2_evaluator.py`, `phase_b2.py`, `phase_b2_validation.py` — B2 evaluator, model runner, and deterministic validation
- `analyze_b2.py` — property level replay of saved B2 candidates
- `phase_b3.py` — identical information autonomy isolation experiment
- `METHODOLOGY.md` — experiment design and fairness controls

## Interpretation discipline

A treatment result applies only to the tested task, model, prompt material, and evaluator version. The lab is designed to accumulate evidence rather than turn one result into a universal ranking of development methods.

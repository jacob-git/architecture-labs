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

The first measured run produced a ceiling effect: all five treatments passed with one model interaction and zero repairs. That result is retained rather than hidden because it is evidence that a small, bounded task may not require extensive structure for a capable model.

## Phase B2 — constraint dense task

Phase B2 keeps the same treatment protocol but moves to a harder bounded TTL cache task. The evaluator checks client isolation, write invalidation, TTL expiry, bounded LRU capacity, mutation safety, concurrent reads, legacy response compatibility, and dependency discipline.

Validate the deterministic B2 harness first:

```bash
python -m labs.adp_001.phase_b2_validation
```

Then run one model trial per treatment:

```bash
python -m labs.adp_001.phase_b2
```

Useful controls:

```bash
ADP_LAB_MODEL=gpt-5.6-luna python -m labs.adp_001.phase_b2
ADP_LAB_REPEATS=10 python -m labs.adp_001.phase_b2
ADP_LAB_TREATMENTS=vibe,spec,agentic python -m labs.adp_001.phase_b2
```

Phase B2 writes its aggregate result to:

```text
labs/adp_001/results/phase-b2-latest.json
```

Generated candidates are kept under `results/b2-runs/`.

## Treatment fairness

The model, baseline, output contract, and evaluator remain fixed across treatments. Vibe, intent, spec, and context receive one implementation attempt. Agentic development may receive visible test and dependency feedback and repair up to three times. Hidden evaluator tests are never exposed to any treatment.

## Repository layout

- `baseline.py`, `reference_solution.py`, `tests_visible.py`, `tests_hidden.py` — Phase A and B1 rate limiting task
- `prompts/`, `context/`, `phase_b.py` — B1 treatments and runner
- `b2_baseline.py`, `b2_reference_solution.py` — harder cache task
- `b2_prompts/`, `b2_context/` — B2 treatments and durable repository context
- `b2_tests_visible.py`, `b2_tests_hidden.py` — B2 acceptance and independent evaluation
- `b2_evaluator.py`, `phase_b2.py`, `phase_b2_validation.py` — B2 evaluator, model runner, and deterministic validation
- `METHODOLOGY.md` — experiment design and fairness controls

## Replication

Do not treat a single run as evidence of superiority. Replication begins only after a task demonstrates enough discrimination to avoid a ceiling effect.

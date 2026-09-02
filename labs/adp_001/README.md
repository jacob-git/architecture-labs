# ADP-001 — Comparing AI Development Modes

ADP-001 is the first lab in the AI Development Patterns series. It compares how different AI-assisted development modes perform on the same bounded software change.

## Research claim

Better AI development outcomes may depend not only on model capability, but also on how clearly humans encode intent, specifications, repository context, and verification.

## Compared modes

- Vibe coding
- Intent driven development
- Spec driven development
- Context driven development
- Agentic development

## Phase A

Phase A is deterministic and model independent. It establishes the baseline application, feature contract, visible and hidden tests, a reference solution, prompt treatments, repository guidance, and evaluator structure.

Run:

```bash
python -m labs.adp_001.phase_a
```

A valid Phase A run requires both controls to behave correctly:

- the known-good reference passes all checks,
- the unmodified baseline is rejected.

## Phase B

Phase B uses one fixed real model across the five treatments. Every treatment starts from the same baseline and is scored by the same visible tests, hidden tests, and dependency policy.

The vibe, intent, spec, and context treatments receive one implementation attempt. The agentic treatment may receive visible test and dependency-policy feedback and autonomously repair its implementation up to three times. Hidden evaluator results are never exposed to the model.

Required environment variable:

```bash
export OPENAI_API_KEY="..."
```

Run one trial per treatment:

```bash
python -m labs.adp_001.phase_b
```

Useful controls:

```bash
ADP_LAB_MODEL=gpt-5.6-luna python -m labs.adp_001.phase_b
ADP_LAB_REPEATS=10 python -m labs.adp_001.phase_b
ADP_LAB_TREATMENTS=vibe,spec,agentic python -m labs.adp_001.phase_b
```

The latest aggregate result is written to:

```text
labs/adp_001/results/phase-b-latest.json
```

Individual generated candidates and model summaries are kept under `results/runs/`.

## Feature under test

The shared task is to add per-client fixed-window API rate limiting while preserving existing API behavior and using only the Python standard library.

## Why one feature across all modes?

The experiment is intended to isolate development method rather than feature difficulty. Model runs start from the same baseline and use the same evaluator.

## Files

- `baseline.py` — unchanged starting application
- `spec.py` — frozen feature contract and evaluator properties
- `reference_solution.py` — known-good implementation used to validate Phase A
- `tests_visible.py` — acceptance feedback that may be exposed only according to the treatment protocol
- `tests_hidden.py` — independent evaluator checks; experiment agents must not inspect these
- `prompts/` — treatment prompts for each development mode
- `context/` — durable repository knowledge used by context and agentic treatments
- `evaluator.py` — common result and policy evaluator
- `phase_b.py` — real-model treatment runner
- `METHODOLOGY.md` — experiment design and fairness controls

## Replication

A single Phase B run is exploratory. The initial replication target is 10 independent runs per treatment before drawing conclusions about relative reliability or intervention cost.

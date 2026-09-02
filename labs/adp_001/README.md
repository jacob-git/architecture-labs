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

Expected Phase A result: the reference implementation passes all visible and hidden behavioral tests with zero model calls.

## Feature under test

The shared task is to add per-client fixed-window API rate limiting while preserving existing API behavior and using only the Python standard library.

## Why one feature across all modes?

The experiment is intended to isolate development method rather than feature difficulty. Later model runs must start from the same baseline and use the same evaluator.

## Files

- `baseline.py` — unchanged starting application
- `spec.py` — frozen feature contract and evaluator properties
- `reference_solution.py` — known-good implementation used to validate Phase A
- `tests_visible.py` — acceptance feedback available to implementations
- `tests_hidden.py` — independent evaluator checks; experiment agents must not inspect these
- `prompts/` — treatment prompts for each development mode
- `context/` — durable repository knowledge used by context and agentic treatments
- `evaluator.py` — common result and policy evaluator
- `METHODOLOGY.md` — experiment design and fairness controls

## Next phase

Phase B will run one fixed model across all five treatments and record correctness, hidden-test performance, interventions, repair attempts, model interactions, and constraint compliance. No cross-model comparison should be introduced until the treatment methodology is stable.

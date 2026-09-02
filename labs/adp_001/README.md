# ADP-001 — Comparing AI Development Modes

ADP-001 is the first lab in the AI Development Patterns series. It compares how different AI assisted development modes perform on the same bounded software change.

## Research claim

Better AI development outcomes may depend not only on model capability, but also on how clearly humans encode intent, specifications, repository context, verification, and runtime feedback.

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

## Phase B1 — simple task

B1 produced a ceiling effect: all five treatments passed the bounded rate limiting task with one interaction and zero repairs.

```bash
python -m labs.adp_001.phase_b
```

## Phase B2 — constraint dense task

The replicated 10 run cache comparison produced:

| Treatment | Full passes | Mean score |
|---|---:|---:|
| Vibe | 0/10 | 0.6667 |
| Intent | 0/10 | 0.6667 |
| Context | 6/10 | 0.8667 |
| Spec | 10/10 | 1.0000 |
| Agentic | 10/10 | 1.0000 |

Property level replay is available without new model calls:

```bash
python -m labs.adp_001.analyze_b2
```

## Phase B3 — autonomy with identical information

B3 gave `spec_one_shot` and `agentic_loop` exactly the same initial information. Both passed on the first attempt, so autonomy provided no measurable advantage on that task.

```bash
python -m labs.adp_001.phase_b3
```

## Phase B4 — runtime feedback value

B4 moves from static information quality to integration feedback. Both treatments receive the same feature specification and the same public starting application. The concrete publisher calling convention is a runtime integration detail rather than prompt material.

- `one_shot` gets one implementation attempt.
- `runtime_feedback_loop` receives the identical initial prompt and may use visible integration test failures for up to three repairs.
- Hidden evaluator output is never exposed.

The research question is whether visible runtime feedback improves reliability when static specification quality is held constant but a concrete integration contract must be discovered through execution.

Validate the deterministic harness first:

```bash
python -m labs.adp_001.phase_b4_validation
```

Then run one exploratory pair:

```bash
python -m labs.adp_001.phase_b4
```

B4 writes:

```text
labs/adp_001/results/phase-b4-latest.json
```

Generated candidates are stored under:

```text
labs/adp_001/results/b4-runs/
```

Do not replicate B4 until the exploratory pair confirms the task actually activates the runtime feedback loop.

## Treatment fairness

Within each comparison, the model, initial prompt material, candidate contract, evaluator, and hidden tests remain fixed. Treatment differences are explicitly recorded rather than silently changing the task.

## Interpretation discipline

A result applies only to the tested task, model, prompt material, runtime contract, and evaluator version. ADP-001 is intended to accumulate falsifiable evidence rather than create a universal ranking of development methods.

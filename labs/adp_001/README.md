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
- `runtime_feedback_loop` receives the identical initial prompt and may use visible integration test failures for repair.
- Hidden evaluator output is never exposed.

The exploratory 3 repair run improved from 0.3333 to 0.6667, while a later 8 repair run remained at 0.3333. The trajectory replay showed that extra retries alone do not guarantee convergence.

Replay every saved B4 attempt at individual property granularity with no model calls:

```bash
python -m labs.adp_001.analyze_b4
```

## Phase B5 — repair budget from a fixed starting candidate

B5 removes the initial generation difference from repair budget comparisons.

One initial `PublishingApi` candidate is generated exactly once and frozen. Every repair budget branch starts from that exact same candidate and receives the same visible runtime feedback rules. The default budgets are 0, 1, 3, 5, and 8 repairs.

The first fixed start run produced full recovery at budgets 5 and 8, while budgets 0, 1, and 3 did not fully recover. Because repair generation is still stochastic, a replicated study is needed before estimating a repair budget curve.

Run one fixed start:

```bash
python -m labs.adp_001.phase_b5
```

Override the budgets if needed:

```bash
ADP_B5_REPAIR_BUDGETS=0,1,3,5,8 python -m labs.adp_001.phase_b5
```

## Phase B5 replication — repair budget curve

The replication runner generates multiple independent frozen starts. Within each start, every budget branch begins from exactly the same frozen candidate. Across starts, independently generated starting candidates allow recovery probability and repair cost to be estimated.

The default study uses 10 starts and budgets 0, 1, 3, 5, and 8:

```bash
python -m labs.adp_001.phase_b5_replication
```

For a smaller exploratory replication:

```bash
ADP_B5_STARTS=3 python -m labs.adp_001.phase_b5_replication
```

The summary reports, per budget:

- full recovery count and rate
- mean final evaluator score
- mean repairs actually used
- mean repair token usage
- mean repair tokens among successful recoveries

Artifacts for every start and every repair branch are retained under:

```text
labs/adp_001/results/b5-replication/
```

The aggregate result is written to:

```text
labs/adp_001/results/phase-b5-replication-latest.json
```

## Treatment fairness

Within each comparison, the model, initial prompt material, candidate contract, evaluator, and hidden tests remain fixed. Within every B5 replication start, all budget branches use the same frozen candidate. Treatment differences are explicitly recorded rather than silently changing the task.

## Interpretation discipline

A result applies only to the tested task, model, prompt material, runtime contract, and evaluator version. ADP-001 is intended to accumulate falsifiable evidence rather than create a universal ranking of development methods.

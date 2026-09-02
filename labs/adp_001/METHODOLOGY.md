# ADP-001 Methodology

## Research question

When the same software change is attempted under different AI development patterns, how do specification quality, repository context, and agent autonomy affect correctness, constraint compliance, and human intervention?

## Phase A

Phase A validates the experiment itself with no model calls. It establishes a deterministic baseline, frozen feature goal, visible and hidden tests, a known good reference implementation, repository context artifacts, treatment prompts, and a reusable result schema.

The positive control must pass. The unmodified baseline must be rejected because it does not implement the requested feature.

## Phase B1 — simple task

B1 compares five treatments on a small rate limiting task:

1. Vibe coding
2. Intent driven development
3. Spec driven development
4. Context driven development
5. Agentic development

The first real model comparison produced a ceiling effect: all five treatments passed. That result is retained because it demonstrates that a simple bounded task may not discriminate among development patterns for a capable model.

## Phase B2 — constraint dense task

B2 keeps the five treatment structure but uses a bounded TTL cache task with interacting requirements around client isolation, invalidation, TTL expiry, LRU capacity, mutation safety, concurrency, compatibility, and dependency policy.

The 10 run replication produced:

- Vibe: 0/10 full passes, mean score 0.6667
- Intent: 0/10 full passes, mean score 0.6667
- Context: 6/10 full passes, mean score 0.8667
- Spec: 10/10 full passes, mean score 1.0000
- Agentic: 10/10 full passes, mean score 1.0000

These results apply only to the tested model, task, evaluator, and prompt material. They do not establish a universal ranking.

### B2 property replay

The original B2 evaluator records suite level results. `analyze_b2.py` replays saved final candidates against each individual visible and hidden test property without making new model calls. This preserves the original model outputs while producing a failure matrix suitable for deeper analysis.

## Phase B3 — autonomy isolation

B2 cannot establish an autonomy advantage because the agentic treatment also received richer initial information and required zero repairs in the replicated batch.

B3 isolates autonomy by comparing two treatments:

1. `spec_one_shot`
2. `agentic_loop`

Both receive exactly the same initial baseline, full feature specification, architecture guidance, engineering rules, and agent guidance. The initial prompt is byte for byte identical across the two treatments and its digest is recorded in the result.

The only treatment difference is execution protocol:

- `spec_one_shot` receives one model implementation call.
- `agentic_loop` receives the same initial call and may receive visible test and dependency policy feedback for up to three autonomous repair attempts.

Hidden evaluator output is never supplied as feedback.

If both treatments pass on the first attempt, B3 provides evidence that autonomous repair was unnecessary for that task rather than evidence of an autonomy advantage. If the one shot treatment fails while the agentic loop repairs visible failures and improves final hidden evaluation, that provides direct evidence of value from iterative autonomous verification under otherwise equal initial information.

## Common fairness controls

Within each comparison batch:

- the same model alias and API protocol are used,
- each trial starts from the same baseline,
- the candidate interface is fixed,
- hidden tests are unchanged across treatments,
- hidden evaluator output is never exposed to the model,
- repository commit and cryptographic experiment digests are recorded,
- one run is treated as exploratory and replication is required before comparative claims.

## Metrics

Primary metrics include:

- full evaluator pass rate,
- evaluator score,
- individual property pass rate when available,
- dependency policy compliance,
- model interactions,
- autonomous repair attempts,
- token usage when reported by the provider,
- model latency as descriptive metadata.

Elapsed wall clock time is not treated as a primary quality measure because infrastructure latency can dominate it.

## Hypothesis

As task complexity and constraint density increase, explicit specifications and durable repository context will tend to improve reliability. Autonomous verification and repair may add value when a correct implementation cannot be reached reliably from the initial information alone.

This is a falsifiable hypothesis. Simpler treatments may perform equally well on simple tasks, and autonomy may provide no measurable benefit when the first implementation already satisfies the evaluator.

## Versioning

ADP-001 is permanent. Material changes to the task, evaluator, model protocol, candidate contract, hidden properties, information exposure, or autonomy rules create a new phase or explicit methodology version rather than silently replacing earlier results.

# ADP-001 Methodology

## Research question

When the same software change is attempted under different AI development patterns, how do specification quality, repository context, and agent autonomy affect correctness, constraint compliance, and human intervention?

## Phase A purpose

Phase A validates the experiment itself. It makes no model calls and draws no conclusion about which development pattern is better.

The phase establishes:

- one deterministic Python baseline,
- one frozen feature goal,
- visible acceptance tests,
- hidden evaluator properties,
- a known-good reference implementation,
- repository context artifacts,
- five development-mode prompt treatments,
- a result schema suitable for later model runs.

Phase A uses a positive control and a negative control. The reference implementation must pass the evaluator, and the unmodified baseline must be rejected because it does not implement the feature.

## Independent variable

Development mode is the independent variable. Phase B keeps the model, baseline repository, feature, candidate interface, and evaluator fixed while changing the information and autonomy treatment.

Treatments:

1. Vibe coding
2. Intent driven development
3. Spec driven development
4. Context driven development
5. Agentic development

## Feature task

Add per-client fixed-window API rate limiting.

Visible requirements include a 10-request limit per 60 seconds, HTTP 429 for excess requests, preservation of existing behavior, no third-party runtime dependencies, and automated tests.

## Hidden evaluation

Hidden properties test aspects that should follow from a robust implementation but are not all spelled out in the shortest treatments:

- 10th/11th request boundary,
- independent client limits,
- window reset,
- legacy response compatibility,
- concurrent accounting,
- dependency policy.

Experiment agents must not inspect hidden tests. Hidden test output is used only by the evaluator and is never supplied as repair feedback.

## Phase B protocol

Phase B uses one model alias for every treatment in a run. The default is `gpt-5.6-luna`, and `ADP_LAB_MODEL` may override it. A study intended for publication should record the actual resolved model returned by the API and the repository commit used for the run.

All treatments receive the same baseline source and the same candidate-module interface required by the evaluator. This common harness contract is not considered treatment information.

Information exposure differs by treatment:

- **Vibe:** short natural-language feature request plus baseline.
- **Intent:** outcome and explicit constraints plus baseline.
- **Spec:** detailed functional, engineering, and acceptance requirements plus baseline.
- **Context:** intent plus durable architecture, engineering, and agent guidance plus baseline.
- **Agentic:** specification plus durable repository guidance plus baseline, with permission to autonomously iterate on visible validation feedback.

Vibe, intent, spec, and context receive one model implementation call per trial. Agentic may receive up to three repair calls after its first implementation when visible tests or dependency-policy checks fail.

The agentic repair loop receives only:

- the original allowed treatment material,
- its current implementation,
- visible test output,
- dependency-policy output.

It never receives hidden test output.

## Primary metrics

- full evaluator pass rate,
- evaluator score,
- visible test pass rate,
- hidden test pass rate,
- dependency-policy compliance,
- model interactions,
- autonomous repair attempts,
- generated test artifact size,
- token usage when reported by the provider,
- model latency as descriptive metadata.

Elapsed wall-clock time is not a primary quality measure because infrastructure latency can dominate it.

## Fairness controls

Each trial must start from the same baseline source. The evaluator and hidden tests must remain unchanged across treatments. The same model alias and API protocol must be used within a comparison batch.

The runner records cryptographic digests of the baseline, hidden evaluator, and treatment prompt material so later results can be tied to the exact experiment definition.

## Replication

A single run per treatment is exploratory and must not be presented as a stable ranking. Ten independent runs per treatment is the initial target before drawing comparative conclusions.

After the treatment protocol is stable, a later phase may repeat the experiment across multiple models to test whether treatment effects generalize.

## Hypothesis

As task complexity and constraint density increase, structured intent, durable repository context, explicit specifications, and autonomous verification will tend to improve reliability and reduce corrective human intervention.

This is a falsifiable hypothesis, not an assumed conclusion. Simpler treatments may perform as well as or better than structured treatments on trivial tasks.

## Versioning

ADP-001 is permanent. Material changes to the task, evaluator, model protocol, candidate contract, hidden properties, or autonomy rules must create a new phase or explicit methodology version rather than silently replacing prior results.

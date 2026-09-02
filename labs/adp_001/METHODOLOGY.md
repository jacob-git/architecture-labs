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

## Independent variable

Development mode is the independent variable. Later phases will keep the model, baseline repository, feature, and evaluator fixed while changing only the information and autonomy treatment.

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

Experiment agents must not inspect hidden tests.

## Primary metrics for Phase B

- visible test pass rate,
- hidden test pass rate,
- constraint compliance,
- human interventions,
- corrective prompts,
- model interactions,
- autonomous repair attempts,
- unnecessary files changed,
- final completeness.

Elapsed wall-clock time will be recorded when useful but will not be a primary quality measure because infrastructure latency can dominate it.

## Fairness controls

Phase B should use the same model and model configuration for every treatment. Each run must start from the same baseline commit. The evaluator and hidden tests must remain unchanged across treatments.

Each treatment should be replicated before drawing conclusions. Ten independent runs per treatment is the initial target.

## Hypothesis

As task complexity and constraint density increase, structured intent, durable repository context, explicit specifications, and autonomous verification will tend to improve reliability and reduce corrective human intervention.

This is a falsifiable hypothesis, not an assumed conclusion. Simpler treatments may perform as well as or better than structured treatments on trivial tasks.

## Versioning

ADP-001 is permanent. Material changes to the task, evaluator, model protocol, or hidden properties must create a new phase or explicit methodology version rather than silently replacing prior results.

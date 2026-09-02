# ADP-001 Research Report

## From Vibe Coding to Agentic Development

**Study:** ADP-001 — Comparing AI Development Modes  
**Repository:** `jacob-git/architecture-labs`  
**Model used in measured runs:** `gpt-5.6-luna`  
**Report date:** September 2, 2026

## Abstract

AI assisted software development is often discussed as a single capability: give a model a task and evaluate the code it returns. In practice, development workflows differ in how much intent, specification, repository context, validation, runtime feedback, and autonomous repair they provide.

ADP-001 tests those differences through a sequence of controlled Python experiments. The study begins with a simple rate limiting task, moves to a constraint dense cache implementation, isolates autonomy under identical initial information, introduces a runtime integration mismatch, and finally measures recovery as repair budget increases from a fixed starting candidate.

The results do not support a universal ranking of development styles. Instead, they support a more conditional conclusion: simple tasks may not benefit from heavy structure, explicit specifications become more valuable as hidden engineering constraints accumulate, repository context improves some classes of behavior without guaranteeing complete correctness, runtime feedback can recover missing integration knowledge, and larger autonomous repair budgets show diminishing returns.

The strongest replicated findings were:

- On a simple bounded task, all five development treatments passed in the exploratory comparison.
- On the constraint dense cache task, vibe and intent treatments produced 0/10 full passes, context produced 6/10, and spec and agentic treatments produced 10/10 each.
- Property level replay showed that vibe and intent implementations consistently missed mutation safety, while exact TTL boundary behavior varied substantially by treatment.
- When specification and repository context were held identical, one shot spec and agentic execution both passed immediately, so autonomy added no measurable value on that task.
- In the replicated repair budget study, recovery increased from 0% at budgets 0 and 1, to 30% at budget 3 and 60% at budgets 5 and 8. Increasing the budget from 5 to 8 did not increase full recovery in the ten start sample, while mean repair token use rose materially.

These results suggest that reliable AI development should be designed around three distinct questions: what information the model receives, what reality the agent can observe, and how much bounded opportunity it receives to repair.

## Research Question

When the same software change is attempted under different AI development patterns, how do specification quality, repository context, runtime feedback, and autonomous repair affect correctness and intervention cost?

The working hypothesis was:

> As task complexity and constraint density increase, structured intent, durable repository context, explicit specifications, and autonomous verification will tend to improve reliability and reduce corrective human intervention.

The experiments were designed to allow this hypothesis to fail. In particular, a simpler treatment was allowed to perform as well as a more structured treatment when the task did not require additional structure.

## Development Treatments

ADP-001 begins with five development modes.

### Vibe coding

A short natural language request communicates the desired change with little formal structure.

### Intent driven development

The model receives the desired outcome and important constraints, but not a detailed behavioral contract.

### Spec driven development

The model receives explicit functional requirements, engineering constraints, and acceptance criteria.

### Context driven development

The model receives intent plus durable repository architecture and engineering guidance.

### Agentic development

The model receives strong engineering information and can, when the protocol permits, use visible validation feedback to repair its implementation autonomously.

These labels describe the treatments in this lab. They are not claimed as universal industry definitions.

## Phase B1: Simple Task and the Ceiling Effect

The first real model comparison used a small per client fixed window API rate limiting task.

All five treatments scored 1.0 in the exploratory run:

| Treatment | Score | Model interactions | Repairs |
|---|---:|---:|---:|
| Vibe | 1.0000 | 1 | 0 |
| Intent | 1.0000 | 1 | 0 |
| Spec | 1.0000 | 1 | 0 |
| Context | 1.0000 | 1 | 0 |
| Agentic | 1.0000 | 1 | 0 |

This was not treated as evidence that the methods are equivalent. It exposed a ceiling effect: the task was easy enough for the tested model to infer a correct implementation even from the least structured prompt.

That became the first useful finding of ADP-001:

> More engineering process is not automatically more valuable on a small, well bounded task.

The experiment therefore increased constraint density rather than immediately multiplying repetitions of an uninformative scenario.

## Phase B2: Constraint Dense Cache Task

The next task required a bounded per client TTL response cache while preserving legacy behavior. The evaluator covered:

- successful cached reads
- write invalidation
- TTL expiry
- per client isolation
- nonsticky 404 behavior
- mutation safety
- bounded LRU capacity
- concurrent reads
- exact TTL boundary semantics
- dependency policy

The treatment protocol remained controlled around a single model and common evaluator.

### Replicated result

Ten independent runs per treatment produced:

| Treatment | Full passes | Pass rate | Mean evaluator score |
|---|---:|---:|---:|
| Vibe | 0/10 | 0% | 0.6667 |
| Intent | 0/10 | 0% | 0.6667 |
| Context | 6/10 | 60% | 0.8667 |
| Spec | 10/10 | 100% | 1.0000 |
| Agentic | 10/10 | 100% | 1.0000 |

This was the first phase where the information treatments separated consistently.

The result does not establish that spec driven development is universally superior. It does show that, for this constraint dense task and model, the explicit specification treatment was sufficient for complete reliability across the ten run sample.

The agentic treatment also achieved 10/10, but it used zero repair attempts. That is important: the result did not yet demonstrate an autonomy advantage.

## Property Level Replay

The saved B2 candidates were replayed against individual evaluator properties with no additional model calls.

| Property | Vibe | Intent | Context | Spec | Agentic |
|---|---:|---:|---:|---:|---:|
| Cached read compatibility | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Write invalidation | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| General TTL expiry | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Client isolation | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| 404 not sticky | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Mutation safety | 0/10 | 0/10 | 10/10 | 10/10 | 10/10 |
| Bounded LRU capacity | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Concurrent reads | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Exact TTL boundary | 10/10 | 2/10 | 6/10 | 10/10 | 10/10 |
| Dependency policy | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |

Two observations matter.

First, vibe coding did not broadly produce unusable software. It passed most of the observable feature behavior. Its failure was concentrated in mutation safety, a subtle correctness property that the loose request did not communicate.

Second, increased structure did not produce a perfectly monotonic ranking at every property. Vibe happened to produce correct exact TTL boundary behavior in all ten runs, while intent produced it in only two and context in six. This is a useful warning against turning the overall result into a simplistic maturity ladder.

A more defensible conclusion is:

> Different forms of engineering information change what the model attends to. Explicit specifications can reduce ambiguity around subtle correctness properties, but more structure does not guarantee improvement on every individual behavior.

## Phase B3: Holding Information Constant

B2 bundled two advantages inside the agentic treatment: strong engineering information and the possibility of autonomous repair.

B3 separated them.

The `spec_one_shot` and `agentic_loop` conditions received exactly the same initial baseline, full specification, and repository context. The only difference was that the agentic condition could use visible validation feedback for repair.

Both conditions passed on the first attempt:

| Treatment | Score | Interactions | Repairs |
|---|---:|---:|---:|
| Spec one shot | 1.0000 | 1 | 0 |
| Agentic loop | 1.0000 | 1 | 0 |

For this task, autonomy provided no measurable benefit because the static information was already sufficient.

This supports a practical ordering principle:

> Improve information quality before assuming that more autonomy is necessary.

## Phase B4: Runtime Feedback Value

B4 introduced an integration condition that could not be completely resolved from the static prompt material. Both treatments received the same feature specification and public application behavior, while the concrete publisher calling convention was discoverable through runtime validation.

The one shot treatment received one implementation attempt. The runtime feedback condition could inspect visible integration failures and repair.

In the first exploratory run:

| Treatment | Broad evaluator score | Interactions | Repairs |
|---|---:|---:|---:|
| One shot | 0.3333 | 1 | 0 |
| Runtime feedback loop | 0.6667 | 4 | 3 |

A property level replay showed a more informative trajectory.

The runtime feedback condition remained at 1/7 properties through attempts 1, 2, and 3, then jumped to 6/7 on attempt 4. The final visible event publication property still failed.

A later run with an eight repair budget stayed at 1/7 properties through all nine attempts.

These two runs show why retry count alone is not a reliable measure of agent capability. Runtime feedback can materially improve a failing implementation, but repair behavior is stochastic and may remain stuck despite additional opportunities.

The phase supports two bounded conclusions:

> Runtime feedback can recover integration knowledge that was unavailable in the original static information.

> Autonomous iteration is not equivalent to autonomous correctness.

## Phase B5: Repair Budget From a Fixed Starting Candidate

B4 still had a methodological weakness for repair budget comparisons: separate runs began from separate stochastic initial candidates.

B5 fixed that by generating one initial candidate, freezing it, and branching each repair budget from the exact same implementation.

In the first fixed start experiment, budgets 0, 1, and 3 did not recover, while budgets 5 and 8 did. Because the repair paths themselves remained stochastic, the eight repair branch happened to converge after only three repairs while the five repair branch used all five.

That result motivated replication across multiple independently generated frozen starts.

## B5 Replication: Recovery Curves Across Ten Fixed Starts

The replicated study generated ten independent frozen starting candidates. Each start was then branched into repair budgets of 0, 1, 3, 5, and 8. Within each start, every budget branch began from the same candidate.

The measured recovery curve was:

| Repair budget | Full passes | Recovery rate | Mean final score | Mean repairs used | Mean repair tokens |
|---|---:|---:|---:|---:|---:|
| 0 | 0/10 | 0% | 0.3333 | 0.0 | 0 |
| 1 | 0/10 | 0% | 0.3666 | 1.0 | 1,733 |
| 3 | 3/10 | 30% | 0.6000 | 2.9 | 4,851 |
| 5 | 6/10 | 60% | 0.7333 | 4.2 | 6,969 |
| 8 | 6/10 | 60% | 0.8000 | 5.8 | 9,764.4 |

Mean repair tokens on successful branches were approximately 4,420 at budget 3, 6,183.83 at budget 5, and 7,441.5 at budget 8.

The strongest observation is the flattening of full recovery between budgets 5 and 8. In this ten start sample, raising the maximum budget from five to eight did not increase full recovery beyond 60%, while mean repair token use increased by roughly 40%.

The higher budget did improve mean final score from 0.7333 to 0.8000, which suggests that some unsuccessful branches moved closer to correctness even when they did not fully recover.

The defensible conclusion is therefore not that five repairs is an optimal universal budget. It is:

> Additional repair opportunities can increase recovery probability, but the marginal reliability benefit can flatten while computational cost continues to rise.

## A Three Dimensional Model for AI Development Reliability

Across the phases, ADP-001 suggests that reliable AI development can be reasoned about along three separate dimensions.

### 1. Information

What does the model know before it acts?

This includes:

- outcome and intent
- constraints
- repository architecture
- engineering rules
- explicit behavioral specifications
- acceptance criteria

B1 and B2 show why this dimension depends on task complexity. A capable model may infer enough for a small task, while subtle constraints become more important as the engineering surface grows.

### 2. Observability

What can the agent learn from reality after it acts?

This includes:

- visible tests
- compiler or type errors
- integration failures
- runtime behavior
- policy validation
- deployment or environment feedback

B4 shows that missing integration knowledge can sometimes be recovered only when execution produces a useful signal.

### 3. Repair Budget

How much bounded opportunity does the agent have to respond to feedback?

This includes:

- maximum repair iterations
- token budget
- latency budget
- termination rules
- escalation conditions

B5 shows that too little repair opportunity can terminate before recovery, while additional retries eventually encounter diminishing returns.

These dimensions can be summarized as:

**Information → Implementation → Observability → Repair → Reliability**

The practical lesson is not to maximize every dimension. It is to provide enough structure for the actual risk and complexity of the task.

## Engineering Implications

### Do not use agent autonomy to compensate for missing specifications by default

If the expected behavior is knowable in advance, representing it explicitly can be cheaper and more reliable than asking an agent to discover it through repeated failures.

### Treat repository context and feature specifications as different assets

B2 showed that repository context improved reliability, especially around mutation safety, but it did not fully substitute for exact behavioral requirements.

Repository context describes how this codebase expects software to be engineered. A feature specification describes what this particular change must do. Mature AI ready repositories need both.

### Give agents observable feedback, not just more turns

B4 showed that repair opportunity without useful convergence can consume repeated model calls without improving correctness. An autonomous loop needs high signal validation, not simply permission to continue.

### Bound autonomy economically

B5 makes repair budget an architecture and cost decision. Additional retries can improve recovery, but they consume tokens and latency. An agentic platform should have stopping, escalation, and budget policies rather than an assumption of indefinite self correction.

### Evaluate properties, not only aggregate success

The B2 property replay revealed insights that the coarse evaluator score hid. Aggregate pass rates are useful, but engineering teams should also ask which safety, compatibility, concurrency, boundary, or integration properties systematically fail.

## Threats to Validity

ADP-001 is intentionally narrow and should not be generalized beyond its evidence.

### Single primary model

The measured experiments used `gpt-5.6-luna`. Different models may respond differently to the same treatment structure.

### Small software tasks

The tasks are bounded Python exercises designed for controlled comparison. They are not substitutes for full repository scale product development.

### Prompt treatment design

The labels vibe, intent, spec, context, and agentic are operationalized through this lab's prompt material. Alternative implementations of the same development styles may produce different results.

### Ten run replication size

Ten runs per treatment or frozen start set are enough to expose patterns in this lab but are not sufficient to estimate universal percentages with high precision.

### Stochastic repair paths

Even when branches share the same starting candidate, each repair call remains a stochastic model generation. B5 therefore estimates recovery opportunity under a budget rather than a deterministic number of steps required.

### Evaluator coverage

A full pass means passing the properties encoded by this evaluator. It does not prove absence of all defects.

## What ADP-001 Does and Does Not Claim

ADP-001 does **not** claim:

- vibe coding is always bad
- specifications always outperform other workflows
- five repairs is an optimal budget
- agentic development is inherently superior
- the measured percentages generalize to all models and repositories

ADP-001 does provide evidence that, for the tested model and tasks:

- simple tasks can hide differences among development patterns
- explicit behavioral specifications can materially improve reliability on constraint dense work
- repository context can improve important engineering properties without replacing a feature specification
- autonomy may add no value when the initial information is already sufficient
- runtime feedback can enable recovery when static information is incomplete
- additional repair budget can improve recovery probability
- repair budgets can reach diminishing returns before correctness is guaranteed

## Practical Decision Guide

For a small and reversible task, a lightweight request may be sufficient.

For a task with important behavioral boundaries, encode the specification explicitly.

For work inside a mature codebase, provide durable repository context in addition to the feature specification.

For integration work where reality contains information unavailable at prompt time, give the agent observable validation feedback.

For autonomous repair, define a bounded budget and an escalation path rather than assuming retries eventually become correctness.

## Conclusion

ADP-001 began with a simple question: does the way we structure AI development affect software quality?

The experiments produced a more useful answer than a ranking of development styles.

The value of structure depends on the problem.

When the task was simple, every treatment succeeded. When the task accumulated subtle constraints, explicit specification and repository context mattered. When information was already sufficient, autonomy added nothing. When runtime knowledge was missing, feedback created a path to recovery. When the repair budget increased, recovery improved until the observed full pass rate flattened while token cost continued to rise.

The emerging principle is:

> Give the model the right information. Give the agent a way to observe reality. Give it enough bounded opportunity to repair. Do not assume that more context, more autonomy, or more retries are automatically better.

That is the direction ADP-001 suggests for AI ready engineering: not maximum automation, but deliberately engineered information, observability, and bounded autonomy.

## Reproduction

The experiment source, prompts, deterministic controls, evaluators, saved candidate artifacts, and runners are contained in this repository under `labs/adp_001/`.

Key commands:

```bash
python -m labs.adp_001.phase_a
python -m labs.adp_001.phase_b
python -m labs.adp_001.phase_b2_validation
python -m labs.adp_001.phase_b2
python -m labs.adp_001.analyze_b2
python -m labs.adp_001.phase_b3
python -m labs.adp_001.phase_b4_validation
python -m labs.adp_001.phase_b4
python -m labs.adp_001.analyze_b4
python -m labs.adp_001.phase_b5
python -m labs.adp_001.phase_b5_replication
```

For exact measured results, preserve the recorded repository commit, prompt digests, hidden test digests, model alias, and generated result JSON files associated with each run.
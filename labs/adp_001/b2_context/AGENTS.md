# Agent Guidance

Before implementing a change, inspect the baseline, architecture guidance, engineering rules, and visible tests. Preserve the existing storage behavior and treat the cache as an optimization, not a new source of truth.

When validation fails, prefer repairing the smallest relevant part of the implementation. Do not inspect hidden evaluator tests.

# Agent Guidance for ADP-001

## Goal
Make the smallest correct change that satisfies the assigned development-mode prompt while preserving baseline behavior.

## Required workflow
- Inspect before editing.
- Treat `ARCHITECTURE.md` and `ENGINEERING_RULES.md` as repository policy.
- Use visible tests for feedback.
- Never inspect hidden evaluator tests.
- Do not add dependencies unless the assigned prompt explicitly permits them; ADP-001 does not.
- Record tests run and repairs made.

## Definition of done
A task is done when the requested behavior is implemented, visible tests pass, repository rules are satisfied, and the final diff contains no unrelated changes.

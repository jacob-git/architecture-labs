# Architecture Labs

Public, reproducible experiments for testing architecture claims against observable behavior.

This repository is the evidence workspace behind the architecture models and technical writing published at [jacobpallattu.com](https://jacobpallattu.com). Each lab keeps its question, method, fixed inputs, executable harness, results policy, limitations, and revisions together.

## Lab standard

Every lab should make these inspectable:

1. research question and falsifiable hypothesis
2. fictional or openly licensed test environment
3. fixed scenarios and expected outcomes
4. baseline and experimental paths
5. observable measurements without chain-of-thought
6. failures, limitations, and resulting revisions
7. exact reproduction commands

A passing experiment is evidence only for the tested implementation, corpus, configuration, and versions. It is not a certification or a universal safety claim. Negative results remain part of the record.

## Current labs

| Lab | Question | Status |
|---|---|---|
| [AEG Lab #001: Governing Agent Tool Execution](labs/aeg_001/) | Can an independent governance boundary prevent unsafe or over-broad execution while preserving legitimate tool use? | Phase A and Phase B v2 measured |

## Related public work

- [AEG Architecture Model](https://jacobpallattu.com/architecture/aeg)
- [AEG Practical Model Kit](https://jacobpallattu.com/architecture/aeg/kit)
- [AEG Intent Gate](https://github.com/jacob-git/aeg-intent-gate)
- [AEG Intent Gate Starter](https://github.com/jacob-git/aeg-intent-gate-starter)

All environments and identities used by the labs are fictional. No employer systems, internal projects, customer data, production credentials, or private operational details belong in this repository.

## Python

The lab harnesses target Python 3.11 or newer and use the standard library at runtime.

```bash
python -m unittest discover -s tests
python -m labs.aeg_001.phase_a
```

## License

Code and documentation in this repository are available under the [MIT License](LICENSE), unless a lab explicitly states otherwise.

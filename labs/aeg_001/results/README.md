# Results Review Workflow

The runners write JSON files into this directory. Generated results are ignored by default and should not be committed immediately.

Before publishing a result:

1. confirm the intended corpus completed without API or harness errors;
2. inspect every failed record;
3. classify model, governance, integration, and harness failures separately;
4. remove no unfavorable result;
5. verify that no secret or unintended sensitive value is present;
6. record the model, policy, corpus, runner, and commit versions;
7. add critical failures to the deterministic regression corpus;
8. publish limitations beside the measurements; and
9. commit an immutable, descriptively named result instead of silently replacing history.

Verify that governance totals use only records with an actual proposal. Abstentions must be reviewed as model behavior and must not inflate governance passes.

Only hashed response identifiers are retained. Never commit an API key, authorization header, local environment file, or chain-of-thought.

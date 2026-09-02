# Spec Driven Prompt

Implement per-client fixed-window API rate limiting.

## Functional requirements
1. Each client may make at most 10 requests during a 60 second window.
2. The 10th request must succeed when the underlying endpoint would succeed.
3. The 11th request in the same window must return HTTP 429 with `{\"error\": \"rate_limited\"}`.
4. Limits are isolated by client identity.
5. A new 60 second window restores capacity.
6. Existing endpoint status codes and response payloads must remain unchanged for requests that are not rate limited.

## Engineering constraints
- Python standard library only for runtime behavior.
- Do not change the public behavior of the existing API except for the new 429 response.
- The implementation must be safe when requests arrive concurrently.
- Add tests covering boundaries, isolation, reset, compatibility, and concurrency.

## Acceptance criteria
- All existing tests pass.
- All new visible tests pass.
- No third party runtime dependency is introduced.
- The change is limited to files necessary for the feature and tests.

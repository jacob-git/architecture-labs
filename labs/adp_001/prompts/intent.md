# Intent Driven Prompt

## Outcome
Protect the API from one client consuming excessive request capacity.

## Constraints
- Allow up to 10 requests per client in each 60 second window.
- Reject excess requests with HTTP 429.
- Preserve existing endpoint behavior for allowed requests.
- Do not add third party runtime dependencies.
- Add automated tests.

Choose an implementation that fits the existing codebase and keeps the change easy to understand and operate.

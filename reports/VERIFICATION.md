# Verification

Verified on Windows with Python 3.13, local Ollama and qwen2.5:1.5b.

- 20 workflow tests passed in the project environment after the final routing-schema change.
- The original live routing check passed 2/6; see evaluation-baseline.json.
- Final six-case synthetic development check: 5/6 passed (category and escalation only). The application-error case was over-escalated. These cases informed prompt changes and are not a held-out benchmark.
- Manual inspection found remaining draft problems: unsupported shipping restrictions, refund-processing implications, and internal-agent wording instead of customer-facing language. Routing success does NOT establish reply quality. Escalated proposals cannot be sent by the normal approval path; all routine proposals require human editing/review.
- HTTP routes, persistence, race handling and exact approved outbox text were exercised through FastAPI TestClient.
- JavaScript syntax was checked. Full visual/browser interaction testing was unavailable because the browser-control runtime failed to initialize.
- The test environment reports a Starlette/httpx deprecation warning; tests still pass.
- GitHub CI runs software tests only, without Ollama.

No production deployment, real customer messages, or real business outcomes were tested or claimed.

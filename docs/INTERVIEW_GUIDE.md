# Interview preparation

## A short pitch

“I built Support Studio, a local AI-assisted support workflow using FastAPI, SQLite, and Ollama. It retrieves fictional policies and generates structured reply proposals. A server-side state machine requires human approval before simulated delivery. I added revision checks, transactional audit events, duplicate-delivery protection, and tests for failure and concurrency cases.”

Explain that this was built with AI assistance. Do not claim independent authorship of every line, production deployment, real customer usage, measured business savings, or expertise in tools the project does not use.

## Questions you should be able to answer

**How is this different from a chatbot?** A chatbot mainly produces text. This application stores work items, constrains transitions, requires approval, and records decisions. The model is one part of the workflow.

**What makes it an agent?** It performs a bounded sequence of retrieval, proposal generation, validation, and routing. It is not an autonomous agent with arbitrary tool access.

**Where is human-in-the-loop enforced?** In the backend, not just in the UI. Delivery accepts only an approved ticket at the expected revision. Approval saves the exact text to be delivered.

**Why SQLite?** It is simple to run locally, persists across restarts, and supports transactions and uniqueness constraints. A multi-user deployment would need operational decisions about a server database, auth, isolation, migrations, and workers.

**What if two reviewers act at once?** The ticket revision is checked under a write transaction. Only one action with that revision commits. The other gets 409 and must refresh.

**Can a ticket cause the model to send a message?** There is no model-exposed sending tool. All delivery is simulated and requires server-side approval. This does not make the generated text immune to prompt injection.

**Why structured output?** It makes categories, priority, source IDs, and routing decisions machine-parseable. Pydantic still validates the returned JSON; a model can fail even when given a schema.

**How do you prevent hallucinations?** Retrieval, policy instructions, ID checks, and human review reduce some risks. They do not prove correctness. The backend prevents certain actions regardless of draft content.

**Does the audit trail identify who approved?** No. There is no authentication in this local version. It records actions and text, not verified identities, and database owners can modify it.

**Why not LangGraph?** The current workflow is small enough for explicit Python functions and persisted states. LangGraph would be a possible future orchestration choice, not a technology used in this implementation.

**How did you evaluate it?** Separate deterministic workflow tests from real-model development examples. Report the exact recorded result in `reports/evaluation.json`, its six-case sample size, and the fact that it checks routing rather than reply correctness.

**What would production require?** Authentication, reviewer roles, tenant isolation, data retention, rate limits, background workers, operational logging without secrets, stronger policy retrieval, broader evaluations, and carefully scoped external integrations.

## Resume wording you can substantiate after learning the code

- Built a local customer-support workflow using FastAPI, SQLite, and Ollama for policy retrieval, structured response drafting, and human review.
- Implemented revision-based conflict detection, transactional audit events, and a simulated outbox that requires approval and rejects duplicate delivery.
- Tested approval bypass attempts, stale updates, model failures, and persistence; documented a small synthetic model-routing evaluation.

Do not add LangGraph, vector databases, cloud deployment, real email automation, or production-scale claims to this project's skills until you implement and verify them.

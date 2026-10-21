# Understand Support Studio from end to end

## 1. What problem does it solve?

A support representative needs a useful draft, the policy behind it, and a reliable review process. This app proposes a response but leaves decisions to a human. It operates on fictional tickets and never sends real messages.

## 2. Follow one ticket

The browser sends subject and body to `POST /tickets`. Pydantic strips whitespace and rejects empty or oversized fields. `Store.create` inserts the ticket with revision 1 and a creation event.

Clicking Analyze sends that revision. `main.py` verifies the ticket is new or rejected. `agent.retrieve` tokenizes the ticket and policies, ranks word overlap, selects up to three policies, and always includes the general review policy.

`Ollama.generate` sends a system instruction, the ticket, policies, and a Pydantic-derived JSON schema to `/api/chat`. Qwen proposes a category, priority, summary, draft, source IDs, and escalation decision. This is inference: no model training or fine-tuning happens.

`analyze` parses the result and rejects references outside the retrieved policy set. It retries invalid output once. Deterministic rules can force escalation even if the model says it is safe. Citing only the generic review policy also forces escalation.

The result moves the ticket to review or escalated. `Store.transition` checks the revision again, so a second concurrent analysis cannot overwrite a first result. It records the analysis snapshot in the audit event.

In review, the user can edit the draft. Approval saves the exact edited text and increments the revision. Simulated delivery reads that saved text, creates one outbox row, and marks the ticket sent in one transaction. The model never receives a send tool.

## 3. Files

| File | Responsibility |
|---|---|
| `main.py` | HTTP routes, input contracts, error responses, transition permissions |
| `agent.py` | Retrieval, Ollama transport, structured proposal, source checks, escalation rules |
| `store.py` | SQLite tables, transactional updates, revision checks, audit events, outbox |
| `policies.json` | Six fictional policy records with stable IDs |
| `static/index.html` | Queue, editor, source display, decisions, audit timeline |
| `tests/test_workflow.py` | Model-independent behavioral tests |
| `evaluate.py` | Small real-model routing check |
| `.github/workflows/tests.yml` | CI test execution |

## 4. Why a state machine?

It defines allowed transitions. “Approved” is a persisted server state, not a button color. Even if a caller skips the browser and calls simulate-send directly, the server rejects a ticket that is not approved.

Revision numbers implement optimistic concurrency: the caller says which version it reviewed. The transaction rejects a mismatch. `BEGIN IMMEDIATE` serializes writers; the expensive model call happens before that lock. SQLite's unique constraint on `outbox.ticket_id` provides an additional duplicate-delivery guard.

## 5. Why not call this fully autonomous?

The LLM drafts and proposes routing. Python enforces the state machine. A human authorizes the reply. There is no open-ended planning loop, LangGraph graph, model-selected function execution, or actual email sender. “Agent” here means a bounded AI-assisted workflow.

## 6. What retrieval does and does not do

The implementation lowercases words and counts overlapping tokens. That is transparent and inexpensive for six policies, but misses semantic similarity and may retrieve a policy because of generic words. This is distinct from Evidence Desk's embedding search. An improvement would compare lexical and embedding retrieval on a labeled support-ticket dataset before replacing it.

## 7. Why validation is limited

A valid JSON shape is a syntax guarantee. A valid policy ID is a reference guarantee. Neither guarantees the draft is true. The human must check the actual draft against the policy text. The system separately enforces stronger action restrictions regardless of what the draft says.

## 8. Errors and recovery

- 422: invalid input; fix the field.
- 404: ticket ID does not exist.
- 409: stale revision or illegal transition; refresh and review current state.
- 502: Ollama unavailable or invalid proposals; no analysis state is committed.

All tickets persist across restart. A failed model call does not silently replace a draft with canned text. Up to two model calls are allowed, each with a timeout, so retry is bounded but latency can still be high.

## 9. Learn by changing it

1. Create an invoice ticket and explain each event in the timeline.
2. Try delivery before approval using `/docs`; expect 409.
3. Approve an edited reply and verify the outbox matches it exactly.
4. Open the same ticket in two tabs. Update one and try a stale action in the other.
5. Stop Ollama, analyze a new ticket, and check that the state remains new.
6. Add a fictional policy and tests for retrieval and escalation before changing prompts.
7. Read the evaluation drafts and record unsupported claims manually; routing scores alone are insufficient.

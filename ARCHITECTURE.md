# Architecture Note

## Agent design

The agent is a standard tool-calling loop against Groq (`openai/gpt-oss-120b`): the
system prompt states the source-precedence and confirmation rules, the model is
offered three tools, and the loop keeps executing tool calls and feeding results back
until the model returns a plain-text answer (`agent.py::run_agent`). Multi-step
requests (e.g. "look up the order, check the account's agreement, check the SOP,
calculate, decide") are handled naturally by this loop rather than a hardcoded
pipeline, since the model chooses how many tool calls it needs and in what order.

## Tool design

Three distinct tools, matching the assessment's minimum requirement:

1. **`search_documents`** — semantic search over the 6 PDFs (ChromaDB), returns
   chunks with reliability metadata (source, status, tier, scope) attached.
2. **`lookup_structured_data`** — queries/calculates over accounts, orders, tickets
   (SQLite), including derived values like "minutes since booking" and "minutes a
   pickup is overdue," computed relative to the dataset snapshot time from the
   workbook README rather than wall-clock time.
3. **`propose_action`** — the state-changing tool (escalation / ticket update /
   follow-up task). It never executes on first call; it always returns a preview
   with a one-time `confirmation_token`. Only a second call with that exact token and
   `confirmed=true` executes and logs the action. A model asked (or manipulated) to
   skip confirmation simply cannot — there's no path to execution without a token
   that only exists after a preview was already shown to the human.

## Document and structured-data handling

- PDFs are chunked (~700 words, 100 overlap) and each chunk is prefixed inline with
  `[SOURCE / STATUS / SCOPE]` before embedding, so the reliability signal travels
  with the content itself rather than living only in a metadata field the model
  might not weight properly.
- The Excel workbook is loaded into SQLite at build time via `run_ingest.py`, not
  hardcoded — the same code path handles any records CalQuity substitutes when
  testing.

## Source reliability & conflict handling (Problem 2)

`doc_registry.py` encodes an explicit precedence tier per document, taken directly
from the policy's own stated rule: **signed customer agreement (tier 1) > current
policy/SOP (tier 2) > product docs (tier 3) > deprecated docs (tier 99, never
authoritative)**. `search_documents` sorts results by this tier (boosting the
caller's own account-scoped agreement when relevant) and returns a
`precedence_reminder` alongside every result. Historical ticket resolutions are
deliberately *not* retrievable through the document-search tool at all — they only
appear via structured ticket lookups, and the system prompt explicitly instructs the
model to never treat `historical_resolution` fields as policy, since two of the seven
tickets in the pack contain resolutions that contradict current policy (TKT-450,
TKT-451) — this is a deliberate test case, not an edge case we can ignore.

## Access control (Requirement 2)

Enforced at the data layer, not the prompt: `auth.py` resolves a mocked user's
`allowed_account_ids` server-side from their user ID before the agent loop even
starts. That value is injected as a fixed argument into every `lookup_structured_data`
and `propose_action` call in `agent.py::_execute_tool` — the model's own arguments for
scoping are never trusted. `db.py` then filters in SQL. A restricted-viewer role
demoed in the app (locked to `ACCT-003`) returns a hard `access_denied` for any other
account regardless of how the request is phrased.

## Major technical trade-offs

- **SQLite over MySQL/Postgres:** the dataset is ~20 rows total; a file-based DB
  removes an external dependency and deploys as part of the same build step, at the
  cost of not reflecting a "real" production data layer.
- **Rules-based dashboard over a second LLM call (Problem 1):** the issue-detection
  view uses explainable heuristics (keyword clustering, SLA-percentage thresholds)
  rather than asking an LLM to "spot patterns." For a small, auditable dataset,
  deterministic and cheap beats non-deterministic and expensive, and it's easier to
  explain in the demo why something was flagged.
- **In-memory pending-action store:** the confirmation-token registry resets on
  server restart. Fine for a stateless demo/assessment; a production version would
  persist pending actions with an expiry.
- **No real auth:** user identity is a dropdown, per the assessment's explicit
  allowance to mock authentication — but the *scoping logic* it feeds into is real
  and enforced identically to how a real auth system's output would be used.

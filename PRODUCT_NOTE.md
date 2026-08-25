# Product Note

## Additional problem chosen: Problem 1 (Proactive Issue Detection)

Implemented as an "Issue Radar" tab, separate from chat, for authorised staff only.
It runs three explainable checks over the ticket/order data rather than a reactive
chat query:

- **SLA alerts** — flags P1-shaped open tickets against the account's actual SLA
  (contract override if one exists, else plan default from the current policy),
  marking them AT_RISK or BREACHED based on elapsed time vs. target.
- **Recurring/cross-account issues** — clusters open tickets by keyword theme and
  flags when 2+ tickets share a theme, distinguishing single-account repeats from
  issues hitting multiple customers at once (the more urgent signal).
- **Unusual order patterns** — currently flags carrier-fault pickups still
  unresolved past the scheduled window.

I chose this over Problem 2 as the "extra" because Problem 2 (trust/reliability) is
effectively load-bearing for Requirement 1 anyway — a system that doesn't handle
conflicting sources correctly would fail the base assessment, not just miss a bonus.
So it's addressed thoroughly in the core design (see Architecture Note) while Problem
1 gets a genuinely separate, additive feature.

## What I'd build next, in priority order

1. **Real severity field on tickets.** The current SLA-alert logic infers P1 from
   keywords because the dataset has no severity column — a real system needs
   structured severity at ticket creation, not text-sniffing.
2. **Customer-facing chatbot as a second surface**, reusing the same tools/data
   layer with a different (tighter) access-control scope — the assessment explicitly
   allows supporting both contexts, and the account-scoping groundwork is already
   there.
3. **Streaming responses** in the chat UI — right now the user waits for the full
   tool loop to finish before seeing anything, which feels slow on multi-step
   questions.
4. **Persisted action log with audit trail UI** — right now confirmed actions write
   to a JSON file; a real ops tool needs a searchable history of who confirmed what
   and when.
5. **Feedback loop on answers** (thumbs up/down per response) feeding into a review
   queue — directly useful for catching cases where the model's source-precedence
   reasoning was wrong, before it erodes trust.

## What I intentionally left out

- Real SSO/authentication (explicitly allowed to mock).
- A production message queue / async job handling for the action tool — it's
  synchronous, fine for a demo, not for real ticket-system integration latency.
- Reranking or hybrid search on document retrieval — the corpus is 6 documents;
  embedding similarity alone is sufficient at this scale and adding a reranker would
  be over-engineering for the given data pack.
- Handling for documents outside the 6 supplied (e.g. an eventual customer-agreement
  upload flow) — out of scope per "use only the supplied data pack."

## One metric to judge usefulness

**Percentage of chat sessions resolved without a human escalation or a corrected
answer.** This captures both halves of what matters here: the system should resolve
what it can confidently resolve (not escalate everything reflexively), and when it
does answer, the answer should hold up — a session that ends in a staff member
manually overriding the bot's answer is functionally a failure even if the bot never
said "I don't know."

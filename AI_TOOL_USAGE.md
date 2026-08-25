# AI Tool Usage

I used Claude (Anthropic) throughout this project as a coding assistant:

- Scaffolding the backend (Flask app structure, ChromaDB ingestion pipeline, SQLite
  schema loading, the tool-calling agent loop) and the frontend (React chat UI with
  tool-trace display and a confirmation modal).
- Reviewing the assessment brief against the implementation to check all minimum
  requirements were covered (3 distinct tools, confirmation flow, access control,
  multi-step support).
- Verifying the correct current Groq model ID and confirming it supports
  function/tool calling, after the originally-used model was deprecated.
- Testing the access-control logic, the confirmation-token flow, and the dashboard
  heuristics directly against the supplied data pack before wiring up the LLM layer.

I reviewed, ran, and adjusted the generated code myself rather than using it
unmodified — in particular the source-reliability tiering logic, the access-control
enforcement points, and the confirmation-token flow were designed and verified
against the assessment's specific requirements rather than accepted as-is.

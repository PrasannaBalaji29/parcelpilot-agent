# ParcelPilot Internal Support/Ops Assistant

An AI agent for authorised ParcelPilot staff to investigate accounts, orders, and
tickets, answer policy questions with source-reliability awareness, and take
confirmed actions (escalations, ticket updates). Built for the CalQuity AI Engineer
assessment.

- **Chatbot type:** Internal support/operations (staff-facing, not customer-facing)
- **Additional problem addressed:** Problem 1 (Proactive Issue Detection) + Problem 2
  (Trust & Reliability, built into the core design)

## Tech stack

- Backend: Python, Flask, Groq (`openai/gpt-oss-120b`) for tool-calling
- Document retrieval: ChromaDB (local vector store) + PyMuPDF for PDF text extraction
- Structured data: SQLite (loaded from the supplied Excel workbook)
- Frontend: React + Vite

## Project structure

```
parcelpilot-agent/
  backend/
    app/
      doc_registry.py    # source reliability tiers (agreement > policy > product doc > deprecated)
      ingest.py           # PDF -> ChromaDB
      db.py                # xlsx -> SQLite, access-controlled query functions
      auth.py              # mocked staff roles
      agent.py             # Groq tool-calling loop
      dashboard.py         # Problem 1: proactive issue detection
      main.py               # Flask API
      tools/
        doc_search.py       # Tool 1
        data_lookup.py      # Tool 2
        action_tool.py       # Tool 3 (confirm-before-execute)
    data/
      raw_docs/            # the 6 supplied PDFs
      ParcelPilot_Assessment_Data.xlsx
    run_ingest.py           # builds SQLite + ChromaDB from the data pack
  frontend/
    src/
      App.jsx, ChatView.jsx, DashboardView.jsx, index.css
```

## Setup & run (local)

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install sentence-transformers   # embedding model for ChromaDB

cp .env.example .env
# edit .env and set GROQ_API_KEY=your_key_here

python run_ingest.py            # builds SQLite DB + ChromaDB index from the data pack (run once, or after data changes)
python -m app.main              # starts Flask on http://localhost:5000
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env            # VITE_API_BASE=http://localhost:5000
npm run dev                     # http://localhost:5173
```

Open the frontend URL, pick a mock user from the dropdown (Rohit/Maya = full staff
access, Read-only Viewer = locked to ACCT-003 only, to demo access control), and
start chatting.

## Try these

- "Can Northstar cancel ORD-1001 without a cancellation fee? Explain why."
- "A pickup is three hours late because of carrier fault. Should I get a service credit?"
- "Escalate TKT-501" (watch the confirmation card — it won't execute until you approve)
- Switch to the **Read-only Viewer** user and ask about ACCT-001 — it will be denied.
- Check the **Issue Radar** tab for the Problem 1 dashboard.

## Deployment

- **Backend:** Render (Web Service). Build command: `pip install -r requirements.txt && python run_ingest.py`.
  Start command: `gunicorn -w 2 -b 0.0.0.0:$PORT app.main:app`. Set `GROQ_API_KEY` and
  `GROQ_MODEL` as environment variables in the Render dashboard.
- **Frontend:** Vercel. Set `VITE_API_BASE` to the deployed Render backend URL.

## Documents

- [Architecture Note](./ARCHITECTURE.md)
- [Product Note](./PRODUCT_NOTE.md)
- [AI Tool Usage](./AI_TOOL_USAGE.md)

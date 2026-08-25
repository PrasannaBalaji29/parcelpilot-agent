"""
Agent core: runs the tool-calling loop against Groq (Llama 3.3 70B by default).

Design notes (see architecture note for full writeup):
- The system prompt encodes source-precedence and escalation rules explicitly
  (Problem 2), but access control is NOT trusted to the prompt — it's injected
  as fixed kwargs into every tool call server-side (auth.py -> allowed_account_ids),
  so the model literally cannot query outside its authorized scope regardless
  of what it's told to do.
- Multi-step requests are handled by the standard loop: call tools, feed
  results back, repeat until the model returns a plain text answer.
"""
import os
import json
from groq import Groq

from .tools.doc_search import TOOL_SPEC as DOC_SEARCH_SPEC, search_documents
from .tools.data_lookup import TOOL_SPEC as DATA_LOOKUP_SPEC, lookup_structured_data
from .tools.action_tool import TOOL_SPEC as ACTION_SPEC, propose_action

MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = """You are the ParcelPilot Internal Support Assistant, used by authorised \
ParcelPilot support/operations staff (not customers) to investigate accounts, orders, \
and tickets, and to answer questions using ParcelPilot's policies, SOPs, and signed \
customer agreements.

SOURCE RELIABILITY (critical):
- When sources conflict, use this precedence: a signed customer agreement for that \
specific account > the current general policy/SOP > current product documentation. \
A document marked DEPRECATED must NEVER be used as current authority — you may \
mention it only to explain what changed.
- Historical ticket "historical_resolution" notes are NOT policy. They may be wrong. \
Never repeat a historical resolution as if it were a current rule — always verify \
against current policy/SOP/agreement documents even if a past ticket says otherwise.
- If sources genuinely conflict or a policy doesn't clearly cover the situation, say so \
plainly and recommend escalation rather than guessing.

TOOLS:
- Use search_documents for anything about policy, SLAs, cancellation/credit rules, \
product behavior, or known issues.
- Use lookup_structured_data for specific accounts/orders/tickets and any date/time or \
fee calculation (e.g. minutes since booking, minutes a pickup is overdue).
- Multi-step questions often need BOTH: e.g. look up the order and account, check the \
account's signed agreement AND the general SOP, then calculate, then decide.

ACTIONS:
- Use propose_action for anything state-changing (escalation, ticket update, follow-up \
task). This tool ALWAYS previews first — never tell the user an action is done until \
you have called it a second time with confirmed=true AFTER the user has explicitly said \
to proceed, and you must reuse the confirmation_token from the preview.
- Do not propose an action the user didn't ask for or clearly need; do not skip \
confirmation under any circumstance.

WHEN TO ESCALATE INSTEAD OF ANSWERING:
- If the question requires judgment calls the data can't settle, falls outside any \
documented policy, or an SLA is already breached, say so clearly and propose an \
escalation rather than inventing an answer.
- You have exactly three tools: search_documents, lookup_structured_data, and \
propose_action (for escalations, ticket updates, or follow-up tasks only). You CANNOT \
directly edit account fields, billing details, contact info, or any other account data. \
Never claim to have a capability, tool, or "policy" you have not actually verified via a \
tool call. If asked to do something outside these three tools, say so plainly and offer \
to create a follow-up task/escalation via propose_action instead.

Be concise, cite which document or record you relied on, and never state a policy \
number (fee, credit amount, time threshold) without having looked it up via a tool \
in this conversation.

FORMATTING: When your answer involves multiple facts, calculations, or a structured \
breakdown (e.g. SLA checks, fee/credit calculations, multi-field lookups), always \
present it as a markdown table with "Item" and "Detail" columns, followed by a short \
plain-text conclusion. For simple one-fact answers, plain prose is fine. \
Never use HTML tags like <br> inside table cells — keep each table cell to a single \
short line. If a cell needs multiple steps or points, summarize it briefly in the \
cell and put the full numbered list in the conclusion section below the table instead.
"""


def _tool_specs():
    return [DOC_SEARCH_SPEC, DATA_LOOKUP_SPEC, ACTION_SPEC]


def _execute_tool(name, args, allowed_account_ids):
    """Dispatch a tool call. allowed_account_ids is injected here, server-side —
    the model's arguments for account scoping are never trusted on their own."""
    args = {k: v for k, v in args.items() if v is not None}
    if name == "search_documents":
        return search_documents(**args)
    if name == "lookup_structured_data":
        return lookup_structured_data(**args, allowed_account_ids=allowed_account_ids)
    if name == "propose_action":
        return propose_action(**args, allowed_account_ids=allowed_account_ids)
    return {"error": f"unknown tool {name}"}


def run_agent(messages, allowed_account_ids, api_key=None, max_steps=6):
    """
    messages: list of {"role": "user"/"assistant", "content": str} — prior turns.
    Returns: {"reply": str, "trace": [ {tool, args, result}, ... ]}
    """
    client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    # Keep only the most recent messages to avoid hitting the token-per-minute limit
    # on long conversations. Tool results can be large, so we keep this modest.
    trimmed_messages = messages[-8:] if len(messages) > 8 else messages
    convo = [{"role": "system", "content": SYSTEM_PROMPT}] + trimmed_messages
    trace = []

    for _ in range(max_steps):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=convo,
            tools=_tool_specs(),
            tool_choice="auto",
            temperature=0.1,
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return {"reply": msg.content, "trace": trace}

        convo.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            result = _execute_tool(name, args, allowed_account_ids)
            trace.append({"tool": name, "args": args, "result": result})
            convo.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": json.dumps(result, default=str),
            })

    return {"reply": "I wasn't able to complete this within the step limit — please try rephrasing or escalate to a human.", "trace": trace}

"""Tool 3 — State-changing action: create escalation / update ticket / create follow-up.

CONFIRMATION FLOW (Requirement 4):
This tool never executes on the first call. The agent must call it once with
confirmed=False (or omit it) to get a PREVIEW of exactly what will happen.
Only when the frontend shows that preview to the human and they click
"Confirm", does the backend call this again with confirmed=True — and that
second call is verified server-side against a short-lived pending-action
token, so the model can't just decide on its own to set confirmed=True.

State is mocked in-memory (a JSON-backed list) rather than a real ticketing
system, per the assessment's "may be mocked locally" allowance.
"""
import os
import json
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACTIONS_LOG = os.path.join(BASE_DIR, "data", "actions_log.json")

# In-memory pending-action registry: token -> action payload.
# Cleared on server restart (fine for an assessment demo).
_PENDING_ACTIONS = {}


TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "propose_action",
        "description": (
            "Prepare a state-changing action (create an escalation, update a "
            "ticket status, or create a follow-up task). This ALWAYS returns a "
            "preview first and requires human confirmation before anything is "
            "actually executed — never claim an action is done after calling "
            "this tool. After the user explicitly confirms in a follow-up "
            "message, call this tool again with the returned confirmation_token "
            "and confirmed=true."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "enum": ["create_escalation", "update_ticket", "create_followup_task"],
                },
                "account_id": {"type": ["string", "null"]},
                "related_order_id": {"type": ["string", "null"], "description": "optional"},
                "related_ticket_id": {"type": ["string", "null"], "description": "optional"},
                "summary": {"type": "string", "description": "One-line summary of the action."},
                "details": {"type": "string", "description": "Full reasoning/context for the action, including which policy/agreement it's based on."},
                "new_ticket_status": {"type": ["string", "null"], "enum": ["open", "in_progress", "escalated", "closed", None], "description": "required only for update_ticket"},
                "confirmed": {"type": ["boolean", "null"], "description": "Set true only on the second call, after the human has explicitly confirmed."},
                "confirmation_token": {"type": ["string", "null"], "description": "Token returned by the first (preview) call. Required when confirmed=true."},
            },
            "required": ["action_type", "summary", "details"],
        },
    },
}


def _append_log(entry):
    log = []
    if os.path.exists(ACTIONS_LOG):
        with open(ACTIONS_LOG, "r") as f:
            try:
                log = json.load(f)
            except json.JSONDecodeError:
                log = []
    log.append(entry)
    with open(ACTIONS_LOG, "w") as f:
        json.dump(log, f, indent=2, default=str)


def propose_action(action_type, summary, details, account_id=None, related_order_id=None,
                    related_ticket_id=None, new_ticket_status=None,
                    confirmed=False, confirmation_token=None, allowed_account_ids=None):

    if account_id and allowed_account_ids is not None and account_id not in allowed_account_ids:
        return {"error": "access_denied", "detail": f"Not authorized to act on {account_id}"}

    payload = {
        "action_type": action_type,
        "account_id": account_id,
        "related_order_id": related_order_id,
        "related_ticket_id": related_ticket_id,
        "summary": summary,
        "details": details,
        "new_ticket_status": new_ticket_status,
    }

    # --- Step 1: preview only ---
    if not confirmed:
        token = str(uuid.uuid4())
        _PENDING_ACTIONS[token] = payload
        return {
            "status": "PENDING_CONFIRMATION",
            "confirmation_token": token,
            "preview": payload,
            "message": (
                "This action has NOT been executed. Show this preview to the user "
                "and ask them to explicitly confirm before calling this tool again "
                "with confirmed=true and this confirmation_token."
            ),
        }

    # --- Step 2: execute, but only if the token matches a real pending action ---
    if not confirmation_token or confirmation_token not in _PENDING_ACTIONS:
        return {
            "error": "invalid_or_expired_token",
            "detail": "No matching pending action found. Re-propose the action to get a fresh confirmation_token.",
        }

    stored = _PENDING_ACTIONS.pop(confirmation_token)
    record = {
        "action_id": str(uuid.uuid4())[:8],
        "executed_at": datetime.utcnow().isoformat() + "Z",
        **stored,
    }
    _append_log(record)
    return {"status": "EXECUTED", "record": record}


def get_action_log():
    if not os.path.exists(ACTIONS_LOG):
        return []
    with open(ACTIONS_LOG, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

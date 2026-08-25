"""
Mocked authentication for authorised ParcelPilot staff.

Real SSO/auth is out of scope for the assessment (explicitly allowed to
mock). What matters is that the *role -> allowed_account_ids* mapping is
resolved server-side, once, at request time — never trusted from the
client and never something the LLM can talk its way around, since it's
injected into tool calls before the model ever runs.
"""

MOCK_USERS = {
    "agent_rohit": {
        "name": "Rohit",
        "role": "support_agent",
        "allowed_account_ids": None,  # None = full staff access (all accounts)
    },
    "agent_maya": {
        "name": "Maya",
        "role": "support_agent",
        "allowed_account_ids": None,
    },
    "viewer_readonly": {
        "name": "Read-only Viewer",
        "role": "restricted_viewer",
        "allowed_account_ids": ["ACCT-003"],  # demo of a locked-down role
    },
}

DEFAULT_USER_ID = "agent_rohit"


def get_user(user_id: str):
    return MOCK_USERS.get(user_id, MOCK_USERS[DEFAULT_USER_ID])

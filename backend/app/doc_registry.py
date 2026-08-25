"""
Source-of-truth registry for every document in the data pack.

This is the core of the trust/reliability handling (Problem 2). Instead of
letting the LLM guess which document "wins" when two sources disagree, we
encode precedence explicitly and pass it into every retrieval result and
every prompt. The precedence order (stated in 01_Support_Policy_v3):

    signed customer agreement  >  current policy/SOP  >  product docs
    >  deprecated policy (never authoritative)
    historical ticket resolutions = context only, may be WRONG, never a source of truth

tier: lower number = higher authority
"""

DOCUMENTS = {
    "01_Support_Policy_v3_CURRENT.pdf": {
        "tier": 2,
        "label": "Current Support Policy (v3)",
        "status": "CURRENT",
        "scope": "general",  # applies to all accounts unless overridden
        "note": "Defines default SLAs and explicit source-precedence rule.",
    },
    "02_Support_Policy_v2_DEPRECATED.pdf": {
        "tier": 99,
        "label": "Support Policy v2 (DEPRECATED)",
        "status": "DEPRECATED",
        "scope": "general",
        "note": "Superseded 1 May 2026. Must never be cited as current authority.",
    },
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf": {
        "tier": 2,
        "label": "Cancellation & Service Credit SOP (v4)",
        "status": "CURRENT",
        "scope": "general",
        "note": "Default cancellation/credit rules; overridable by signed agreements.",
    },
    "04_Product_Operations_Guide_and_Known_Issues.pdf": {
        "tier": 3,
        "label": "Product Operations Guide & Known Issues",
        "status": "CURRENT",
        "scope": "general",
        "note": "Product behavior + live known-issue list (KI-208, KI-211).",
    },
    "05_Northstar_Logistics_Enterprise_Agreement.pdf": {
        "tier": 1,
        "label": "Northstar Logistics Enterprise Agreement",
        "status": "CURRENT",
        "scope": "account:ACCT-001",
        "note": "Signed agreement. Overrides general policy for ACCT-001 only.",
    },
    "06_LumenWorks_Service_Agreement.pdf": {
        "tier": 1,
        "label": "LumenWorks Service Agreement",
        "status": "CURRENT",
        "scope": "account:ACCT-002",
        "note": "Signed agreement. Overrides general policy for ACCT-002 only.",
    },
}


def get_doc_meta(filename: str) -> dict:
    return DOCUMENTS.get(filename, {"tier": 50, "label": filename, "status": "UNKNOWN", "scope": "general"})

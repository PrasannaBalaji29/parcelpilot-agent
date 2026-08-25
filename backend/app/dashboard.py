"""
Problem 1 — Proactive Issue Detection.

Runs a handful of deliberately simple, explainable heuristics over the
ticket/order data rather than another LLM call — for a dataset this small,
a transparent rules engine is more trustworthy and faster than asking an
LLM to "notice patterns" (see architecture note: trade-off #3).

Detections:
  1. Multiple open tickets referencing the same known issue / same theme
     (keyword clustering on subject+description).
  2. Tickets whose account+severity implies an SLA that is at risk or
     already breached, based on account plan + the CURRENT support policy
     defaults (Northstar/LumenWorks use their contract SLAs instead).
  3. Same product issue affecting multiple distinct accounts at once.
  4. Unusual order patterns (e.g. carrier-fault pickup still not resolved).
"""
from datetime import datetime, timedelta
from collections import defaultdict
from . import db

DATASET_SNAPSHOT = datetime(2026, 8, 16, 11, 0, 0)

# Default SLA minutes by plan for P1 (from Support Policy v3). Contract accounts
# override via CONTRACT_SLA_OVERRIDES.
DEFAULT_P1_MINUTES = {"Enterprise": 30, "Growth": 120, "Standard": 240}
CONTRACT_SLA_OVERRIDES = {
    "ACCT-001": 15,   # Northstar: 15 min, 24x7 P1
}

KEYWORD_THEMES = {
    "bulk_upload_failure": ["bulk upload", "csv", "upload fails", "upload failure"],
    "shipment_creation_failure": ["shipment creation", "http 500", "creating shipment"],
    "pickup_status_lag": ["still shows booked", "pickup", "webhook"],
    "security_incident": ["api key", "credential", "security", "exposure"],
}


def _theme_for_ticket(ticket):
    text = f"{ticket.get('subject','')} {ticket.get('description','')}".lower()
    for theme, keywords in KEYWORD_THEMES.items():
        if any(kw in text for kw in keywords):
            return theme
    return None


def compute_dashboard():
    tickets = db.list_all_tickets_unscoped()
    orders = db.list_all_orders_unscoped()
    open_tickets = [t for t in tickets if t["status"] == "open"]

    # --- 1 & 3: theme clustering (also flags cross-account spread) ---
    theme_groups = defaultdict(list)
    for t in open_tickets:
        theme = _theme_for_ticket(t)
        if theme:
            theme_groups[theme].append(t)

    recurring_issues = []
    for theme, group in theme_groups.items():
        if len(group) >= 2:
            accounts = sorted(set(t["account_id"] for t in group))
            recurring_issues.append({
                "theme": theme,
                "ticket_count": len(group),
                "accounts_affected": accounts,
                "cross_account": len(accounts) > 1,
                "ticket_ids": [t["ticket_id"] for t in group],
                "severity_hint": "high" if len(accounts) > 1 else "medium",
            })

    # --- 2: SLA risk on open tickets ---
    conn_accounts = {a["account_id"]: a for a in _all_accounts()}

    sla_alerts = []
    for t in open_tickets:
        acct = conn_accounts.get(t["account_id"])
        if not acct:
            continue
        plan = acct["plan"]
        p1_minutes = CONTRACT_SLA_OVERRIDES.get(acct["account_id"], DEFAULT_P1_MINUTES.get(plan, 240))
        created = datetime.fromisoformat(str(t["created_at"]))
        minutes_open = (DATASET_SNAPSHOT - created).total_seconds() / 60
        # Only flag tickets that read as P1-severity (outage/security keywords) —
        # a cheap proxy since the dataset doesn't have an explicit severity column.
        text = f"{t['subject']} {t['description']}".lower()
        looks_p1 = any(k in text for k in ["all shipment creation", "http 500", "api key", "security", "credential"])
        if looks_p1:
            pct_of_sla = minutes_open / p1_minutes if p1_minutes else 0
            sla_alerts.append({
                "ticket_id": t["ticket_id"],
                "account_id": t["account_id"],
                "subject": t["subject"],
                "minutes_open": round(minutes_open, 1),
                "p1_sla_minutes": p1_minutes,
                "status": "BREACHED" if pct_of_sla >= 1 else ("AT_RISK" if pct_of_sla >= 0.7 else "OK"),
            })

    sla_alerts = [a for a in sla_alerts if a["status"] != "OK"]

    # --- 4: unusual order patterns ---
    order_flags = []
    for o in orders:
        if o.get("carrier_fault") and o["status"] == "BOOKED" and not o.get("pickup_actual_at"):
            order_flags.append({
                "order_id": o["order_id"],
                "account_id": o["account_id"],
                "flag": "carrier_fault_pickup_unresolved",
                "detail": "Carrier-fault flag set, still not picked up as of dataset snapshot.",
            })

    return {
        "dataset_snapshot": DATASET_SNAPSHOT.isoformat(),
        "recurring_issues": sorted(recurring_issues, key=lambda x: -x["ticket_count"]),
        "sla_alerts": sla_alerts,
        "unusual_order_patterns": order_flags,
        "open_ticket_count": len(open_tickets),
    }


def _all_accounts():
    import sqlite3
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM accounts").fetchall()
    conn.close()
    return [dict(r) for r in rows]

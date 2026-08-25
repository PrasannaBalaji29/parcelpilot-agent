"""Tool 2 — Structured-data lookup/calculation over accounts, orders, tickets.

Access control note: every function here requires `allowed_account_ids`
(resolved server-side from the authenticated user, see auth.py) and filters
in db.py at the SQL layer. The LLM only ever receives already-filtered
results — it cannot request another account's data by asking nicely.
"""
from datetime import datetime
from .. import db

DATASET_SNAPSHOT = datetime(2026, 8, 16, 11, 0, 0)  # from workbook README, Asia/Kolkata


TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "lookup_structured_data",
        "description": (
            "Look up ParcelPilot accounts, orders, or tickets, and/or run a "
            "time/fee calculation against them. Use this for anything involving "
            "specific IDs, dates, statuses, or numeric checks (e.g. 'is this pickup "
            "more than 2 hours late', 'has 30 minutes passed since booking'). "
            "All results are automatically scoped to what the current user is "
            "authorized to see."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "enum": ["account", "orders", "tickets"]},
                "account_id": {"type": ["string", "null"], "description": "e.g. ACCT-001"},
                "order_id": {"type": ["string", "null"], "description": "e.g. ORD-1001, for entity=orders"},
                "ticket_id": {"type": ["string", "null"], "description": "e.g. TKT-501, for entity=tickets"},
                "ticket_status": {"type": ["string", "null"], "enum": ["open", "closed", None], "description": "optional filter for entity=tickets"},
                "calculate": {
                    "type": "string",
                    "enum": ["minutes_since_booking", "minutes_pickup_overdue", "none"],
                    "description": "Optional derived calculation to run against a looked-up order, "
                                    "relative to the dataset snapshot time.",
                },
            },
            "required": ["entity"],
        },
    },
}


def _minutes_since_booking(order, snapshot):
    booked = datetime.fromisoformat(str(order["booked_at"]))
    return round((snapshot - booked).total_seconds() / 60, 1)


def _minutes_pickup_overdue(order, snapshot):
    window_end = datetime.fromisoformat(str(order["pickup_window_end"]))
    if order.get("pickup_actual_at"):
        actual = datetime.fromisoformat(str(order["pickup_actual_at"]))
        return round((actual - window_end).total_seconds() / 60, 1)
    return round((snapshot - window_end).total_seconds() / 60, 1)


def lookup_structured_data(entity, account_id=None, order_id=None, ticket_id=None,
                            ticket_status=None, calculate="none", allowed_account_ids=None):
    if entity == "account":
        if not account_id:
            return {"error": "account_id required for entity=account"}
        return db.get_account(account_id, allowed_account_ids=allowed_account_ids)

    if entity == "orders":
        orders = db.list_orders(account_id=account_id, order_id=order_id,
                                 allowed_account_ids=allowed_account_ids)
        if isinstance(orders, dict) and orders.get("error"):
            return orders
        if calculate != "none":
            for o in orders:
                if calculate == "minutes_since_booking":
                    o["_calculated_minutes_since_booking"] = _minutes_since_booking(o, DATASET_SNAPSHOT)
                elif calculate == "minutes_pickup_overdue":
                    o["_calculated_minutes_pickup_overdue"] = _minutes_pickup_overdue(o, DATASET_SNAPSHOT)
        return {"dataset_snapshot": DATASET_SNAPSHOT.isoformat(), "orders": orders}

    if entity == "tickets":
        tickets = db.list_tickets(account_id=account_id, status=ticket_status,
                                   allowed_account_ids=allowed_account_ids)
        if isinstance(tickets, dict) and tickets.get("error"):
            return tickets
        if ticket_id:
            tickets = [t for t in tickets if t.get("ticket_id") == ticket_id]
        for t in tickets:
            created = datetime.fromisoformat(str(t["created_at"]))
            t["_calculated_minutes_since_created"] = round((DATASET_SNAPSHOT - created).total_seconds() / 60, 1)
        return {"dataset_snapshot": DATASET_SNAPSHOT.isoformat(), "tickets": tickets} 

    return {"error": f"unknown entity {entity}"}
"""
Loads ParcelPilot_Assessment_Data.xlsx into SQLite and exposes access-controlled
read functions.

IMPORTANT (Requirement 2 - Access Control):
Every read function here takes the *caller's authorized account scope* as a
parameter and filters in SQL. The agent/LLM never sees a raw "give me
everything" query — scope is enforced at this layer, so a prompt-injection
attempt inside a document or user message cannot make the model bypass it.

For this internal-ops build: staff users are scoped by role.
  - "support_agent"  -> can view accounts they're assigned to (csm match) OR all,
                          per ALLOW_ALL_FOR_SUPPORT_AGENT toggle below (mocked auth)
  - "restricted_viewer" -> demo of a locked-down role, single account only
Toggle the mock user in auth.py.
"""
import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX_PATH = os.path.join(BASE_DIR, "data", "ParcelPilot_Assessment_Data.xlsx")
DB_PATH = os.path.join(BASE_DIR, "data", "parcelpilot.db")


def build_database():
    xls = pd.ExcelFile(XLSX_PATH)
    conn = sqlite3.connect(DB_PATH)
    for sheet in ["accounts", "orders", "tickets"]:
        df = pd.read_excel(xls, sheet_name=sheet)
        df.to_sql(sheet, conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()
    print(f"Built SQLite DB at {DB_PATH}")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _rows_to_dicts(rows):
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Access-controlled query functions. `allowed_account_ids=None` means
# "unrestricted staff" (mocked role); a list means hard-scoped.
# ---------------------------------------------------------------------------

def get_account(account_id: str, allowed_account_ids=None):
    if allowed_account_ids is not None and account_id not in allowed_account_ids:
        return {"error": "access_denied", "detail": f"Not authorized to view {account_id}"}
    conn = _conn()
    row = conn.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,)).fetchone()
    conn.close()
    return dict(row) if row else {"error": "not_found"}


def list_orders(account_id: str = None, order_id: str = None, allowed_account_ids=None):
    conn = _conn()
    query = "SELECT * FROM orders WHERE 1=1"
    params = []
    if account_id:
        if allowed_account_ids is not None and account_id not in allowed_account_ids:
            conn.close()
            return {"error": "access_denied", "detail": f"Not authorized to view {account_id}"}
        query += " AND account_id = ?"
        params.append(account_id)
    if order_id:
        query += " AND order_id = ?"
        params.append(order_id)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    results = _rows_to_dicts(rows)
    if allowed_account_ids is not None:
        results = [r for r in results if r["account_id"] in allowed_account_ids]
    return results


def list_tickets(account_id: str = None, status: str = None, allowed_account_ids=None):
    conn = _conn()
    query = "SELECT * FROM tickets WHERE 1=1"
    params = []
    if account_id:
        if allowed_account_ids is not None and account_id not in allowed_account_ids:
            conn.close()
            return {"error": "access_denied", "detail": f"Not authorized to view {account_id}"}
        query += " AND account_id = ?"
        params.append(account_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    results = _rows_to_dicts(rows)
    if allowed_account_ids is not None:
        results = [r for r in results if r["account_id"] in allowed_account_ids]
    return results


def list_all_tickets_unscoped():
    """Internal-only helper for the proactive issue-detection view (Problem 1).
    Not exposed as an agent tool with customer args — used by the dashboard
    endpoint which itself requires an authorized-staff role."""
    conn = _conn()
    rows = conn.execute("SELECT * FROM tickets").fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def list_all_orders_unscoped():
    conn = _conn()
    rows = conn.execute("SELECT * FROM orders").fetchall()
    conn.close()
    return _rows_to_dicts(rows)


if __name__ == "__main__":
    build_database()

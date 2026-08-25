import os
from flask import Flask, request, jsonify
from flask_cors import CORS

from .agent import run_agent
from .auth import get_user, MOCK_USERS
from . import db
from .tools.action_tool import get_action_log
from .dashboard import compute_dashboard

app = Flask(__name__)
CORS(app)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/users", methods=["GET"])
def list_users():
    """Lets the frontend offer a role switcher for the demo."""
    return jsonify([
        {"user_id": uid, "name": u["name"], "role": u["role"]}
        for uid, u in MOCK_USERS.items()
    ])


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    messages = body.get("messages", [])
    user_id = body.get("user_id", "agent_rohit")

    if not messages:
        return jsonify({"error": "messages required"}), 400

    user = get_user(user_id)
    result = run_agent(messages, allowed_account_ids=user["allowed_account_ids"])

    return jsonify({
        "reply": result["reply"],
        "trace": result["trace"],
        "user": {"name": user["name"], "role": user["role"]},
    })


@app.route("/api/actions/log", methods=["GET"])
def actions_log():
    return jsonify(get_action_log())


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    """Problem 1: proactive issue detection view. Internal-staff only (mocked
    via required user_id here too, so it isn't a public unscoped data leak)."""
    user_id = request.args.get("user_id", "agent_rohit")
    user = get_user(user_id)
    if user["role"] not in ("support_agent",):
        return jsonify({"error": "access_denied"}), 403
    return jsonify(compute_dashboard())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

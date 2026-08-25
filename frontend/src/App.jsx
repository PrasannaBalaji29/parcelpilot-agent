import { useState, useEffect } from "react";
import ChatView from "./ChatView";
import DashboardView from "./DashboardView";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000";

export default function App() {
  const [tab, setTab] = useState("chat");
  const [users, setUsers] = useState([]);
  const [userId, setUserId] = useState("agent_rohit");

  useEffect(() => {
    fetch(`${API_BASE}/api/users`)
      .then((r) => r.json())
      .then(setUsers)
      .catch(() => setUsers([]));
  }, []);

  return (
    <>
      <div className="topbar">
        <div className="brand">
          <span className="brand-mark">PP</span>
          ParcelPilot <span className="divider">/</span> <span className="subtitle">ops console</span>
        </div>
        <div className="tabs">
          <button className={`tab ${tab === "chat" ? "active" : ""}`} onClick={() => setTab("chat")}>
            Chat
          </button>
          <button className={`tab ${tab === "dashboard" ? "active" : ""}`} onClick={() => setTab("dashboard")}>
            Issue Radar
          </button>
        </div>
        <div className="user-select">
          Signed in as
          <select value={userId} onChange={(e) => setUserId(e.target.value)}>
            {users.map((u) => (
              <option key={u.user_id} value={u.user_id}>
                {u.name} ({u.role})
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="main">
        {tab === "chat" ? (
          <ChatView apiBase={API_BASE} userId={userId} />
        ) : (
          <DashboardView apiBase={API_BASE} userId={userId} />
        )}
      </div>
    </>
  );
}

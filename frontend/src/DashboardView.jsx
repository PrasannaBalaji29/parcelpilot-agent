import { useState, useEffect } from "react";

export default function DashboardView({ apiBase, userId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    setError(null);
    fetch(`${apiBase}/api/dashboard?user_id=${userId}`)
      .then((r) => {
        if (!r.ok) throw new Error("access_denied");
        return r.json();
      })
      .then(setData)
      .catch(() => setError("This role doesn't have access to the issue radar."));
  }, [apiBase, userId]);

  if (error) return <div className="dashboard"><div className="empty-state">{error}</div></div>;
  if (!data) return <div className="dashboard"><div className="empty-state">Loading...</div></div>;

  return (
    <div className="dashboard">
      <div className="empty-state">Dataset snapshot: {data.dataset_snapshot} · {data.open_ticket_count} open tickets</div>

      <h2>SLA Alerts</h2>
      {data.sla_alerts.length === 0 ? (
        <div className="empty-state">No P1 tickets currently at risk or breached.</div>
      ) : (
        <div className="card-grid">
          {data.sla_alerts.map((a) => (
            <div key={a.ticket_id} className={`dcard ${a.status === "BREACHED" ? "breached" : "at-risk"}`}>
              <span className={`badge ${a.status}`}>{a.status.replace("_", " ")}</span>
              <div><b>{a.ticket_id}</b> — {a.account_id}</div>
              <div>{a.subject}</div>
              <div style={{ marginTop: 6, color: "var(--text-dim)" }}>
                Open {a.minutes_open} min · SLA target {a.p1_sla_minutes} min
              </div>
            </div>
          ))}
        </div>
      )}

      <h2>Recurring / Cross-Account Issues</h2>
      {data.recurring_issues.length === 0 ? (
        <div className="empty-state">No recurring issue clusters detected right now.</div>
      ) : (
        <div className="card-grid">
          {data.recurring_issues.map((r) => (
            <div key={r.theme} className="dcard">
              <span className="badge info">{r.cross_account ? "cross-account" : "same account"}</span>
              <div><b>{r.theme.replaceAll("_", " ")}</b></div>
              <div style={{ marginTop: 6, color: "var(--text-dim)" }}>
                {r.ticket_count} tickets · accounts: {r.accounts_affected.join(", ")}
              </div>
            </div>
          ))}
        </div>
      )}

      <h2>Unusual Order Patterns</h2>
      {data.unusual_order_patterns.length === 0 ? (
        <div className="empty-state">Nothing unusual detected in current order data.</div>
      ) : (
        <div className="card-grid">
          {data.unusual_order_patterns.map((o) => (
            <div key={o.order_id} className="dcard">
              <span className="badge info">{o.flag.replaceAll("_", " ")}</span>
              <div><b>{o.order_id}</b> — {o.account_id}</div>
              <div style={{ marginTop: 6, color: "var(--text-dim)" }}>{o.detail}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
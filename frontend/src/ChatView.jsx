import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

const TOOL_META = {
  search_documents: { label: "Doc Search", cls: "doc", icon: "\u25A4" },
  lookup_structured_data: { label: "Data Lookup", cls: "data", icon: "\u25C8" },
  propose_action: { label: "Action Draft", cls: "action", icon: "\u26A1" },
};

function ToolTrace({ trace }) {
  const [openIdx, setOpenIdx] = useState(null);
  if (!trace || trace.length === 0) return null;
  return (
    <div className="trace">
      {trace.map((t, i) => {
        const meta = TOOL_META[t.tool] || { label: t.tool, cls: "", icon: "\u{1F527}" };
        return (
          <div key={i}>
            <div className="tool-pill" onClick={() => setOpenIdx(openIdx === i ? null : i)} style={{ cursor: "pointer" }}>
              <span className="icon">{meta.icon}</span>
              {meta.label}
              {t.args?.query ? ` \u2014 "${t.args.query}"` : ""}
              {t.args?.entity ? ` \u2014 ${t.args.entity}${t.args.order_id ? " " + t.args.order_id : ""}${t.args.account_id ? " " + t.args.account_id : ""}` : ""}
            </div>
            {openIdx === i && (
              <div className="tool-details">{JSON.stringify(t.result, null, 2)}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ConfirmCard({ pending, onConfirm, onCancel }) {
  const p = pending.result.preview;
  return (
    <div className="confirm-card">
      <div className="title">⚠️ Confirmation required before this action executes</div>
      <div className="row"><b>Type:</b> {p.action_type}</div>
      {p.account_id && <div className="row"><b>Account:</b> {p.account_id}</div>}
      {p.related_ticket_id && <div className="row"><b>Ticket:</b> {p.related_ticket_id}</div>}
      {p.related_order_id && <div className="row"><b>Order:</b> {p.related_order_id}</div>}
      <div className="row"><b>Summary:</b> {p.summary}</div>
      <div className="row"><b>Details:</b> {p.details}</div>
      <div className="confirm-actions">
        <button className="yes" onClick={onConfirm}>Confirm & Execute</button>
        <button className="no" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default function ChatView({ apiBase, userId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [traces, setTraces] = useState({});
  const [pendingAction, setPendingAction] = useState(null); // { msgIdx, result }
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(overrideText) {
    const text = overrideText ?? input;
    if (!text.trim() || loading) return;

    const newMessages = [...messages, { role: "user", content: text }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);
    setPendingAction(null);

    try {
      const res = await fetch(`${apiBase}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: newMessages, user_id: userId }),
      });
      const data = await res.json();

      const assistantIdx = newMessages.length;
      const updated = [...newMessages, { role: "assistant", content: data.reply }];
      setMessages(updated);
      setTraces((prev) => ({ ...prev, [assistantIdx]: data.trace }));

      const pendingCall = (data.trace || []).find(
        (t) => t.tool === "propose_action" && t.result?.status === "PENDING_CONFIRMATION"
      );
      if (pendingCall) {
        setPendingAction({ msgIdx: assistantIdx, result: pendingCall.result });
      }
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: "Error reaching the backend. Is the Flask server running?" }]);
    } finally {
      setLoading(false);
    }
  }

  function confirmAction() {
    const token = pendingAction.result.confirmation_token;
    setPendingAction(null);
    send(`Yes, please confirm and execute that action now. (confirmation_token: ${token})`);
  }

  function cancelAction() {
    setPendingAction(null);
    send("No, cancel that action. Don't execute it.");
  }

  return (
    <div className="chat-wrap">
      <div className="messages">
        {messages.length === 0 && (
          <div className="msg system-note">
            TRY — "Can Northstar cancel ORD-1001 without a cancellation fee?" · "A pickup for LumenWorks is 3 hours late due to carrier fault, should they get a credit?" · "Escalate TKT-501" · switch to Read-only Viewer and ask about a different account
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i}>
            <div className={`msg ${m.role}`}>
              {m.role === "assistant" ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>{m.content}</ReactMarkdown>
              ) : (
                m.content
              )}
            </div>
            {m.role === "assistant" && <ToolTrace trace={traces[i]} />}
            {pendingAction && pendingAction.msgIdx === i && (
              <ConfirmCard pending={pendingAction} onConfirm={confirmAction} onCancel={cancelAction} />
            )}
          </div>
        ))}
        {loading && <div className="typing">Processing</div>}
        <div ref={bottomRef} />
      </div>
      <div className="composer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask about an account, order, ticket, or policy..."
          disabled={loading}
        />
        <button onClick={() => send()} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
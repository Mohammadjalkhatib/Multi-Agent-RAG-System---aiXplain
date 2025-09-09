import { useState } from "react";
import { ask } from "../api";

export default function AskForm({ onAnswer }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!q.trim()) return;
    setBusy(true);
    try {
      const res = await ask(q); // { data }
      onAnswer?.(res.data);
    } finally { setBusy(false); }
  };

  return (
    <form onSubmit={submit}>
      <h3>2) Ask a question</h3>
      <input
        style={{ width: "100%", padding: 10 }}
        placeholder="e.g., When does this policy take effect for small businesses?"
        value={q}
        onChange={e => setQ(e.target.value)}
      />
      <button disabled={busy || !q.trim()} style={{ marginTop: 10 }}>
        {busy ? "Thinking…" : "Ask"}
      </button>
    </form>
  );
}

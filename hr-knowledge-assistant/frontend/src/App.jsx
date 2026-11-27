import { useEffect, useRef, useState } from "react";
import { streamChat } from "./api.js";

const SUGGESTIONS = [
  "How many sick leaves do I get?",
  "Can I carry it forward?",
  "What is my leave balance?",
  "Do we get stock options?",
];

const newSessionId = () => crypto.randomUUID().replaceAll("-", "");

export default function App() {
  const [employeeId, setEmployeeId] = useState("E1001");
  const [sessionId, setSessionId] = useState(newSessionId);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [messages]);

  // Immutable update of the last (assistant) message.
  const patchLast = (fn) => setMessages((m) => [...m.slice(0, -1), fn(m[m.length - 1])]);

  async function send(question) {
    if (!question.trim() || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", text: question }, { role: "assistant", text: "", steps: [], sources: [] }]);
    try {
      await streamChat(
        { question, employeeId, sessionId },
        {
          onStep: (node) => patchLast((a) => ({ ...a, steps: [...a.steps, node] })),
          onToken: (t) => patchLast((a) => ({ ...a, text: a.text + t })),
          onFinal: (f) => patchLast((a) => ({ ...a, text: f.answer, sources: f.sources, route: f.route })),
        },
      );
    } catch (e) {
      patchLast((a) => ({ ...a, text: `Sorry, something went wrong: ${e.message}` }));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>Nimbus HR Assistant</h1>
        <div className="controls">
          <select value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} aria-label="Employee">
            <option>E1001</option>
            <option>E1002</option>
            <option>E1003</option>
          </select>
          <button onClick={() => { setMessages([]); setSessionId(newSessionId()); }}>New chat</button>
        </div>
      </header>

      <main>
        {messages.length === 0 && (
          <div className="empty">
            <p>Ask anything about leave, benefits, onboarding, WFH or expenses.</p>
            <div className="chips">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.steps?.length > 0 && <div className="steps">{m.steps.join(" → ")}</div>}
            <div className="bubble">{m.text || (busy && i === messages.length - 1 ? "…" : "")}</div>
            {m.sources?.length > 0 && (
              <details className="sources">
                <summary>Sources ({m.sources.length})</summary>
                {m.sources.map((s) => (
                  <div key={s.id}>
                    <b>[{s.id}] {s.source}</b> {s.section && `— ${s.section}`}
                  </div>
                ))}
              </details>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </main>

      <form onSubmit={(e) => { e.preventDefault(); send(input); }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask HR…" disabled={busy} />
        <button type="submit" disabled={busy || !input.trim()}>Send</button>
      </form>
    </div>
  );
}

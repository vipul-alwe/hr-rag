import { useState, useRef, useEffect } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import axios from "axios";
import "./App.css";
import RagDataManager from "./components/rag-data-manager";

const API_BASE = "http://localhost:8000";
const GROUP_OPTIONS = ["test_group_1", "test_group_2"];

type Msg = { id: string; role: "user" | "assistant"; text: string };

function ChatPage() {
  const [groupId, setGroupId] = useState(GROUP_OPTIONS[0]);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    const userMsg: Msg = { id: Date.now().toString(), role: "user", text: trimmed };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      // Get today's date in DD-MM-YYYY format
      const date = new Date();
      const today = date.toISOString().split("T")[0];
      
      const res = await axios.post(`${API_BASE}/ask`, { 
        group_id: groupId, 
        question: trimmed,
        current_date: today 
      });
      const answer = res.data?.answer ?? "No answer returned.";
      const assistantMsg: Msg = { id: (Date.now() + 1).toString(), role: "assistant", text: answer };
      setMessages((m) => [...m, assistantMsg]);
    } catch (err) {
      setMessages((m) => [...m, { id: (Date.now() + 2).toString(), role: "assistant", text: "Error fetching answer." }]);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">KnOML</div>
        <div className="top-controls">
          <select value={groupId} onChange={(e) => setGroupId(e.target.value)}>
            {GROUP_OPTIONS.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
          <nav className="mini-nav">
            <Link to="/">Chat</Link>
            <Link to="/data">Data</Link>
          </nav>
        </div>
      </header>

      <main className="chat-container">
        <div className="chat-window">
          <div className="messages" aria-live="polite">
            {messages.map((m) => (
              <div key={m.id} className={`message ${m.role === "user" ? "user" : "assistant"}`}>
                <div className="bubble">{m.text}</div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          <div className="composer">
            <textarea
              className="composer-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={loading ? "Waiting for response..." : "Send a message (Enter to send, Shift+Enter for newline)"}
              disabled={loading}
              rows={1}
            />
            <div className="composer-actions">
              <button className="btn" onClick={send} disabled={loading || !input.trim()}>
                {loading ? "Thinking..." : "Send"}
              </button>
              <button className="btn secondary" onClick={() => { setMessages([]); setInput(""); }} disabled={loading}>
                Clear
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/data" element={<RagDataManager />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
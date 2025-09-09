import React, { useRef, useState } from "react";

// --- Config ---------------------------------------------------------------
const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

// Convert a filename to a stable doc id
const toDocId = (name = "document") =>
  `doc-${name.replace(/\.[^/.]+$/, "").replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`;

// Try to pull the most useful text field from any aiXplain response
function getBestText(data) {
  if (!data) return "";
  if (typeof data === "string") return data;
  // common shapes
  const cands = [
    data.answer,
    data.output,
    data.message,
    data.text,
    data.result,
    data?.data?.answer,
    data?.data?.output,
    data?.data?.message,
  ].filter(Boolean);
  if (cands.length) return String(cands[0]);
  try {
    return JSON.stringify(data, null, 2);
  } catch (_) {
    return String(data);
  }
}

function classNames(...xs) {
  return xs.filter(Boolean).join(" ");
}

export default function PolicyNavigatorApp() {
  // --- Upload/Index state -------------------------------------------------
  const fileInputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [extracted, setExtracted] = useState("");
  const [indexedCount, setIndexedCount] = useState(0);
  const [autoIndex, setAutoIndex] = useState(true);
  const [lastFilename, setLastFilename] = useState("");

  // --- Ask/Chat state -----------------------------------------------------
  const [mode, setMode] = useState("pipeline"); // "pipeline" | "chat"
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loadingAsk, setLoadingAsk] = useState(false);
  const [raw, setRaw] = useState(null);

  // --- Upload handlers ----------------------------------------------------
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) setSelectedFile(f);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setExtracted("");
    setAnswer("");
    setRaw(null);

    try {
      const fd = new FormData();
      fd.append("file", selectedFile);
      const r = await fetch(`${API_BASE}/upload`, { method: "POST", body: fd });
      if (!r.ok) throw new Error(`Upload failed: ${r.status}`);
      const data = await r.json();
      setExtracted(data.text || "");
      setLastFilename(data.filename || selectedFile.name);

      if (autoIndex && (data.text || "").trim()) {
        const body = {
          items: [
            {
              id: toDocId(data.filename || selectedFile.name),
              text: data.text,
              meta: { filename: data.filename || selectedFile.name, source: "upload" },
            },
          ],
        };
        const ix = await fetch(`${API_BASE}/index`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!ix.ok) throw new Error(`Index failed: ${ix.status}`);
        const j = await ix.json();
        setIndexedCount((c) => c + (j.upserted || body.items.length));
      }
    } catch (err) {
      setExtracted(`⚠️ ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  // --- Ask/Chat -----------------------------------------------------------
  const handleAsk = async () => {
    if (!question.trim()) return;
    setLoadingAsk(true);
    setAnswer("");
    setRaw(null);
    try {
      if (mode === "pipeline") {
        const r = await fetch(`${API_BASE}/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: question.trim(), extra_inputs: {} }),
        });
        const j = await r.json();
        setRaw(j);
        setAnswer(getBestText(j));
      } else {
        const r = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: question.trim(), llm_id: "" }),
        });
        const j = await r.json();
        setRaw(j);
        setAnswer(getBestText(j));
      }
    } catch (err) {
      setAnswer(`⚠️ ${err.message}`);
    } finally {
      setLoadingAsk(false);
    }
  };

  // --- UI -----------------------------------------------------------------
  return (
    <div className="relative min-h-screen bg-[#0b1020] text-white overflow-x-hidden">
      {/* background glow */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-24 -left-20 h-72 w-72 rounded-full bg-fuchsia-600/20 blur-3xl" />
        <div className="absolute top-32 -right-16 h-80 w-80 rounded-full bg-cyan-500/20 blur-3xl" />
        <div className="absolute bottom-10 left-1/3 h-64 w-64 rounded-full bg-indigo-600/20 blur-3xl" />
      </div>

      <header className="mx-auto max-w-6xl px-6 pt-12 pb-6">
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight">
          <span className="bg-gradient-to-r from-cyan-300 via-fuchsia-300 to-indigo-300 bg-clip-text text-transparent">
            Policy Navigator
          </span>
          <span className="text-white/60"> — Agentic RAG</span>
        </h1>
        <p className="mt-3 text-white/70 max-w-3xl">
          Upload policy docs, index them, then ask questions. Answers include references/snippets when your pipeline returns them.
        </p>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-24 space-y-10">
        {/* Upload & Index */}
        <section className="rounded-2xl border border-white/[0.08] bg-white/[0.06] backdrop-blur p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">1) Upload & Index</h2>
            <label className="flex items-center gap-2 text-sm text-white/80 cursor-pointer select-none">
              <input
                type="checkbox"
                className="h-4 w-4 accent-cyan-400"
                checked={autoIndex}
                onChange={(e) => setAutoIndex(e.target.checked)}
              />
              Auto-index after extraction
            </label>
          </div>

          {/* Dropzone */}
          <div
            className={classNames(
              "relative mt-2 rounded-xl border-2 border-dashed p-8 text-center transition",
              dragOver ? "border-cyan-400 bg-cyan-400/5" : "border-white/15"
            )}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
            />
            <div className="flex flex-col items-center">
              <svg className="h-10 w-10 text-white/60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 16V4m0 0 4 4m-4-4-4 4" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M20 16.5a3.5 3.5 0 0 1-3.5 3.5H7.5A3.5 3.5 0 0 1 4 16.5" strokeLinecap="round" />
              </svg>
              <p className="mt-2 text-sm text-white/70">
                Drag & drop a PDF/Word/Image here, or
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="ml-2 inline-flex items-center rounded-lg bg-white/10 px-3 py-1.5 text-sm hover:bg-white/20 transition"
                >
                  Choose file
                </button>
              </p>
              {selectedFile && (
                <p className="mt-2 text-xs text-white/60">Selected: {selectedFile.name}</p>
              )}
              <button
                onClick={handleUpload}
                disabled={!selectedFile || uploading}
                className={classNames(
                  "mt-4 inline-flex items-center justify-center rounded-xl px-4 py-2 font-medium shadow",
                  uploading ? "bg-white/10 text-white/60 cursor-not-allowed" : "bg-cyan-500/90 hover:bg-cyan-400/90 text-black"
                )}
              >
                {uploading ? "Uploading & extracting…" : "Upload & Extract"}
              </button>
            </div>
          </div>

          {/* Extract preview */}
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-lg border border-white/10 bg-black/30 p-4">
              <h3 className="text-sm font-semibold text-white/80">Extracted text preview</h3>
              <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap text-xs text-white/80">
                {extracted || "—"}
              </pre>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/30 p-4">
              <h3 className="text-sm font-semibold text-white/80">Index status</h3>
              <p className="mt-2 text-sm text-white/70">Indexed docs (this session): <span className="font-semibold text-cyan-300">{indexedCount}</span></p>
              {lastFilename && (
                <p className="mt-1 text-xs text-white/60">Last file: {lastFilename}</p>
              )}
            </div>
          </div>
        </section>

        {/* Ask / Chat */}
        <section className="rounded-2xl border border-white/[0.08] bg-white/[0.06] backdrop-blur p-6 shadow-xl">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <h2 className="text-xl font-semibold">2) Ask</h2>
            <div className="flex rounded-full bg-white/10 p-1">
              {[
                { key: "pipeline", label: "Pipeline (RAG)" },
                { key: "chat", label: "Direct Chat" },
              ].map((opt) => (
                <button
                  key={opt.key}
                  onClick={() => setMode(opt.key)}
                  className={classNames(
                    "px-3 py-1.5 text-sm rounded-full transition",
                    mode === opt.key ? "bg-white text-black" : "text-white/80 hover:bg-white/10"
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4 flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={mode === "pipeline" ? "e.g., When does this policy take effect for small businesses?" : "Say hi…"}
              className="flex-1 rounded-xl border border-white/15 bg-black/30 px-4 py-3 text-sm outline-none focus:border-cyan-400/60"
            />
            <button
              onClick={handleAsk}
              disabled={!question.trim() || loadingAsk}
              className={classNames(
                "min-w-[96px] rounded-xl px-4 py-3 text-sm font-medium shadow",
                loadingAsk ? "bg-white/10 text-white/60 cursor-not-allowed" : "bg-fuchsia-500/90 hover:bg-fuchsia-400/90 text-black"
              )}
            >
              {loadingAsk ? "Asking…" : "Ask"}
            </button>
          </div>

          {/* Answer */}
          <div className="mt-6 rounded-xl border border-white/10 bg-black/30 p-4">
            <h3 className="text-sm font-semibold text-white/80">Answer</h3>
            <div className="mt-2 whitespace-pre-wrap text-sm text-white/90 min-h-[3rem]">
              {answer || "—"}
            </div>
          </div>

          {/* Debug panel */}
          <details className="mt-3 group">
            <summary className="cursor-pointer select-none text-xs text-white/60 group-open:text-white/80">Debug (raw response)</summary>
            <pre className="mt-2 max-h-72 overflow-auto rounded-lg border border-white/10 bg-black/50 p-3 text-[11px] text-white/80">
{raw ? JSON.stringify(raw, null, 2) : "—"}
            </pre>
          </details>
        </section>

        {/* Footer */}
        <footer className="text-center text-xs text-white/50">
          API base: <code className="text-white/70">{API_BASE}</code>
        </footer>
      </main>
    </div>
  );
}

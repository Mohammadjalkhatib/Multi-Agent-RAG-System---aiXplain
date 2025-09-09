import { useState } from "react";
import { uploadFile, indexItems } from "../api";

export default function UploadPanel({ onIndexed }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");

  const handleUpload = async () => {
    if (!file) return;
    setStatus("Extracting text…");
    const up = await uploadFile(file); // { text, filename }
    setStatus(`Indexing ${up.filename}…`);
    const docId = crypto.randomUUID();
    await indexItems([{ id: docId, text: up.text, meta: { source: up.filename } }]);
    setStatus(`Indexed ${up.filename}`);
    onIndexed?.(docId);
  };

  return (
    <div>
      <h3>1) Upload & Index</h3>
      <input type="file" accept=".pdf,.docx,.png,.jpg,.jpeg" onChange={e => setFile(e.target.files?.[0] ?? null)} />
      <button onClick={handleUpload} disabled={!file} style={{ marginLeft: 12 }}>Upload</button>
      <div style={{ marginTop: 8, color: "#666" }}>{status}</div>
    </div>
  );
}

export default function AnswerCard({ data }) {
  // Expect a structure from your pipeline like:
  // { output: "...", citations: [{source, snippet, url}], execution_stats: {...} }
  const output = data.output || data.answer || JSON.stringify(data, null, 2);
  const citations = data.citations || data.references || [];

  return (
    <div style={{ marginTop: 24, padding: 16, background: "#fafafa", border: "1px solid #eee" }}>
      <h3>Answer</h3>
      <div style={{ whiteSpace: "pre-wrap" }}>{output}</div>

      {citations.length > 0 && (
        <>
          <h4 style={{ marginTop: 16 }}>References</h4>
          <ul>
            {citations.map((c, i) => (
              <li key={i}>
                <strong>{c.source || c.title || c.url || `Source ${i+1}`}</strong>
                {c.url && (<span> — <a href={c.url} target="_blank">link</a></span>)}
                {c.snippet && <div style={{ color: "#555", marginTop: 4 }}>{c.snippet}</div>}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

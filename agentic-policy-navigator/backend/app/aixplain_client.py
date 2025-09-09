"""
Purpose: Single place for aiXplain integration (upload/extract, index, ask, chat).
Ultimate goal: Reliable end-to-end RAG plumbing with good diagnostics and clean text.
"""

import os, logging, time
from typing import Dict, List, Optional, Any, Union
from aixplain.factories import FileFactory, ModelFactory, IndexFactory, PipelineFactory
from aixplain.modules.model.record import Record
from .settings import settings

logger = logging.getLogger("aixplain")
os.environ.setdefault("AIXPLAIN_API_KEY", settings.AIXPLAIN_API_KEY)

PDF_EXTRACTOR_ID = settings.TOOL_PDF_EXTRACTOR
INDEX_ID = settings.INDEX_ID
PIPELINE_ID = settings.PIPELINE_EXEC_ORDER_RETRIEVAL


# ---------- small helpers ----------

def _first_non_empty(*vals):
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v
        if v not in (None, "", [], {}):
            return v
    return None

def _normalize_output(obj: Any) -> Dict[str, Any]:
    """Normalize aiXplain responses to a dict. Never return None."""
    data = getattr(obj, "data", None)
    if data is None:
        data = obj
    if isinstance(data, str):
        return {"output": data}
    if isinstance(data, dict):
        return data
    if isinstance(data, (list, tuple)):
        return {"output": data}
    return {"output": repr(data)}

def _fix_mojibake(s: str) -> str:
    """Quick, dependency-free text cleaner for common PDF encoding artifacts."""
    repl = {
        "â¢": "•", "â": "–", "â": "—", "â": "’",
        "â": "“", "â": "”", "â¦": "…", "Â·": "·", "Â": "",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    try:
        # latin1 → utf8 heuristic
        alt = s.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
        bad = s.count("Ã")+s.count("Â")+s.count("â")
        bad_alt = alt.count("Ã")+alt.count("Â")+alt.count("â")
        if bad_alt < bad:
            s = alt
    except Exception:
        pass
    return s

def _candidate_payloads(question: str, index_id: Optional[str]) -> List[Dict[str, Any]]:
    """
    Build a comprehensive set of candidate payload shapes for pipelines.
    Covers flat keys, wrapped keys, and chat-like shapes.
    """
    basics = [
        {"query": question},
        {"question": question},
        {"prompt": question},
        {"input": question},
        {"text": question},
        {"q": question},
        {"message": question},
    ]
    if index_id:
        augmented = []
        for b in basics:
            for key in ["index_id", "index", "knowledge_index_id", "indexName", "index_name"]:
                c = dict(b); c[key] = index_id; augmented.append(c)
        basics += augmented

    wrappers = []
    for b in basics:
        wrappers += [{"inputs": b}, {"parameters": b}, {"data": b}, {"payload": b}]

    chat_shape = {"messages": [{"role": "user", "content": question}]}
    if index_id:
        chat_shape["index_id"] = index_id

    # Deduplicate
    seen, out = set(), []
    for obj in basics + wrappers + [chat_shape]:
        key = str(sorted(obj.items()))
        if key not in seen:
            seen.add(key); out.append(obj)
    return out


# ---------- public API used by FastAPI routes ----------

def extract_text_from_file(local_path: str) -> str:
    """
    Upload to aiXplain temp storage, then call the PDFTextExtractor.
    Tries multiple common input shapes; logs timing; returns cleaned text.
    """
    t0 = time.time()
    file_url = FileFactory.upload(local_path, is_temp=True, return_download_link=True)
    logger.info(f"[extract] Uploaded in {time.time()-t0:.2f}s -> {file_url}")

    model = ModelFactory.get(PDF_EXTRACTOR_ID)
    t1 = time.time()
    tries: List[Union[str, Dict[str, str]]] = [
        file_url,
        {"url": file_url},
        {"file": file_url},
        {"document_url": file_url},
        {"input": file_url},
    ]
    last_err = None
    for i, payload in enumerate(tries, 1):
        try:
            res = model.run(payload)
            logger.info(f"[extract] run() try {i} OK in {time.time()-t1:.2f}s (total {time.time()-t0:.2f}s)")
            data = _normalize_output(res)
            text = _first_non_empty(data.get("output"), data.get("text"), data.get("result"), str(data))
            if not isinstance(text, str):
                text = str(text)
            return _fix_mojibake(text)
        except Exception as e:
            last_err = e
            logger.warning(f"[extract] run() try {i} failed: {e}")

    raise RuntimeError(f"PDFTextExtractor failed after {len(tries)} attempts: {last_err}")

def index_texts(docs: List[Dict]) -> Dict:
    """
    Upsert text docs into your aiXplain index.
    Each doc: {id?: str, text: str, meta?: dict}
    """
    index = IndexFactory.get(INDEX_ID)
    records = []
    for d in docs:
        rid = d.get("id")
        txt = d["text"]
        attrs = d.get("meta", {})
        records.append(Record(value=txt, value_type="text", id=rid, uri="", attributes=attrs))
    index.upsert(records)
    return {"count": len(records)}

# app/aixplain_client.py (patch for ask_pipeline)

def ask_pipeline(question: str, extra_inputs: Optional[Dict] = None) -> Dict:
    """
    Run the Executive Order Retrieval Pipeline with robust input-shape coverage.
    Returns a dict with status, any outputs, errors, logs, and the payloads we tried.
    """
    pipeline = PipelineFactory.get(PIPELINE_ID)

    tried: List[Dict[str, Any]] = []
    index_id = INDEX_ID
    extra_inputs = extra_inputs or {}

    def run_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        tried.append(payload.copy())
        t0 = time.time()
        try:
            res = pipeline.run(payload)  # synchronous; SDK waits for completion
            out: Dict[str, Any] = {}

            # unwrap common fields from response object
            for attr in [
                "data", "result", "outputs", "output", "message",
                "status", "error", "elapsed_time", "completed",
                "logs", "trace"
            ]:
                if hasattr(res, attr):
                    out[attr] = getattr(res, attr)

            # if still empty, accept dicts or fall back to str
            if not out:
                if isinstance(res, dict):
                    out = res
                else:
                    out = {"output": str(res)}

            out["_elapsed_local_s"] = round(time.time() - t0, 2)
            return out
        except Exception as e:
            return {"status": "FAILED", "error": str(e), "_elapsed_local_s": round(time.time() - t0, 2)}

    # ---- candidate payloads ---------------------------------------------------
    basics = [
        {"query": question},
        {"question": question},
        {"prompt": question},
        {"input": question},
        {"text": question},
        {"q": question},
        {"message": question},  # some script nodes look for this
        {"messages": [{"role": "user", "content": question}]},  # chat-shaped
    ]

    # versions that include an index using common key names
    with_index = []
    if index_id:
        for b in basics:
            for key in ["index_id", "index", "knowledge_index_id", "knowledgeIndexId", "indexName", "index_name"]:
                obj = dict(b)
                obj[key] = index_id
                with_index.append(obj)

    # wrapped variants some pipelines expect
    wrappers = []
    for b in basics + with_index:
        wrappers.extend([{"inputs": b}, {"parameters": b}, {"data": b}, {"payload": b}])

    # merge everything & apply extra_inputs if provided
    candidates: List[Dict[str, Any]] = []
    for obj in basics + with_index + wrappers:
        merged = dict(obj)
        for k, v in extra_inputs.items():
            if v is not None:
                merged[k] = v
        candidates.append(merged)

    # ---- execution loop -------------------------------------------------------
    last_out: Dict[str, Any] = {"status": "FAILED", "error": "No candidate produced a success."}
    for cand in candidates:
        out = run_payload(cand)
        status = str(out.get("status", "")).upper()
        if status and status != "FAILED":
            out["_used_payload"] = cand
            out["_tried_payloads"] = tried
            return out
        last_out = out

    # final failure with diagnostics
    last_out["_used_payload"] = None
    last_out["_tried_payloads"] = tried
    return last_out


def chat_llm(message: str, llm_id: Optional[str] = None) -> Dict:
    """
    Call a single LLM by ID. Returns {'output': <text>, 'raw': <dict-like>}.
    Purpose: direct chat path (bypasses pipeline).
    Ultimate goal: quick conversational fallback & diagnostics.
    """
    mid = llm_id or settings.LLM_ID
    model = ModelFactory.get(mid)
    res = model.run(message)  # simple text-in, text-out
    data = getattr(res, "data", res)
    if isinstance(data, str):
        return {"output": data, "raw": None}
    if isinstance(data, dict):
        out = data.get("output") or data.get("text") or data.get("result") or str(data)
        return {"output": out if isinstance(out, str) else str(out), "raw": data}
    return {"output": str(res), "raw": None}

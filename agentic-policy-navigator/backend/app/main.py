"""
Purpose: Expose /upload, /index, /ask, /chat endpoints to the React app.
Ultimate goal: End-to-end flow — Upload → Extract → Index → Ask/Chat → Show answers with citations/snippets.
"""
import os
import tempfile
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    UploadResponse, IndexRequest, IndexResponse,
    AskRequest, AskResponse,
    ChatRequest, ChatResponse,  # <= make sure these exist in schemas.py
)
from .aixplain_client import (
    extract_text_from_file, index_texts, ask_pipeline, chat_llm
)
from .settings import settings

# ----- logging FIRST so we see stuff early -----
logging.basicConfig(level=logging.INFO)

# ----- create app BEFORE using @app decorators -----
app = FastAPI(title="Policy Navigator — Agentic RAG API")

# ----- CORS -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- ROUTES -----

@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    # During debugging, keep this PDF-only so the extractor is predictable.
    allowed = {"application/pdf"}
    if file.content_type not in allowed:
        raise HTTPException(415, f"Unsupported content-type: {file.content_type} (PDF only during debug)")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp.flush()
        tmp_path = tmp.name

    try:
        text = extract_text_from_file(tmp_path)
        if not text or not text.strip():
            raise ValueError("No text extracted.")
        return UploadResponse(text=text, filename=file.filename)
    except Exception as e:
        raise HTTPException(500, f"Extraction failed: {e}")
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

@app.post("/index", response_model=IndexResponse)
def index_docs(body: IndexRequest):
    try:
        result = index_texts([i.model_dump() for i in body.items])
        return IndexResponse(upserted=result["count"])
    except Exception as e:
        raise HTTPException(500, f"Indexing failed: {e}")

@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    try:
        data = ask_pipeline(body.question, body.extra_inputs)
        if data is None:
            data = {"error": "Empty response from pipeline"}
        return AskResponse(data=data)
    except Exception as e:
        raise HTTPException(500, f"Pipeline failed: {e}")

@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    """
    Purpose: direct single-LLM chat (bypasses pipeline).
    Ultimate goal: give you a quick 'normal chat' path; set LLM_ID in .env or pass llm_id in the body.
    """
    try:
        ans = chat_llm(body.message, body.llm_id)
        return ChatResponse(output=ans["output"], raw=ans.get("raw"))
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {e}")

from fastapi import HTTPException
from aixplain.factories import PipelineFactory
from .settings import settings

@app.get("/__pipeline_meta")
def pipeline_meta():
    try:
        p = PipelineFactory.get(settings.PIPELINE_ID)
        # What we can safely reveal without dumping internals:
        meta = {
            "id": getattr(p, "id", None),
            "name": getattr(p, "name", None),
            "workspace_id": getattr(p, "workspace_id", None),
            "provider": str(type(p).__name__),
            # Some SDK builds expose these; if absent they'll be None.
            "input_schema": getattr(p, "input_schema", None),
            "spec_inputs": getattr(p, "spec", {}).get("inputs", None) if hasattr(p, "spec") else None,
        }
        return meta
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not load pipeline: {e}")


from typing import Optional, Any, Dict, List
from pydantic import BaseModel
import traceback

class SearchBody(BaseModel):
    q: str
    top_k: Optional[int] = 5

@app.post("/search")
def search_index(body: SearchBody):
    from aixplain.factories import IndexFactory
    from .settings import settings

    idx = IndexFactory.get(settings.INDEX_ID)

    # Try common signatures
    errors: List[str] = []
    res = None
    for call in [
        lambda: idx.search(body.q, top_k=body.top_k or 5),
        lambda: idx.search(query=body.q, top_k=body.top_k or 5),
        lambda: idx.search(query=body.q, k=body.top_k or 5),
        lambda: idx.search(body.q),  # default top_k
    ]:
        try:
            res = call()
            break
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")

    if res is None:
        return {
            "status": "FAILED",
            "error": "All search call signatures failed",
            "trace": errors,
        }

    # Normalize a variety of hit shapes into {id, score, text, attributes}
    def norm(hit: Any) -> Dict[str, Any]:
        h = getattr(hit, "data", None) or hit
        out: Dict[str, Any] = {}
        # Common object attributes
        for k in ("id", "score", "value", "text", "attributes", "metadata"):
            v = getattr(hit, k, None)
            if v is not None and k not in ("value", "metadata"):
                out[k] = v
        # Dict-like
        if isinstance(h, dict):
            out.setdefault("id", h.get("id"))
            out.setdefault("score", h.get("score"))
            text_val = h.get("value") or h.get("text") or h.get("output")
            out["text"] = out.get("text") or text_val or str(h)
            out["attributes"] = out.get("attributes") or h.get("attributes") or h.get("meta") or h.get("metadata")
        else:
            text_val = getattr(hit, "value", None) or getattr(hit, "text", None) or str(h)
            out["text"] = out.get("text") or text_val
            out["attributes"] = out.get("attributes") or getattr(hit, "attributes", None) or getattr(hit, "metadata", None)
        return out

    hits = res if isinstance(res, (list, tuple)) else (res or [])
    return {
        "status": "OK",
        "count": len(hits),
        "results": [norm(h) for h in hits],
    }


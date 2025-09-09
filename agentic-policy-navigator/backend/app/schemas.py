"""
Purpose: Define request/response shapes.
Ultimate goal: explicit API contract so /docs and clients work reliably.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class UploadResponse(BaseModel):
    text: str
    filename: str

class IndexItem(BaseModel):
    id: Optional[str] = None
    text: str
    meta: Optional[Dict[str, Any]] = None

class IndexRequest(BaseModel):
    items: List[IndexItem]

class IndexResponse(BaseModel):
    upserted: int

class AskRequest(BaseModel):
    question: str
    extra_inputs: Optional[Dict[str, Any]] = None

class AskResponse(BaseModel):
    data: Dict[str, Any]

# === New for /chat ===
class ChatRequest(BaseModel):
    message: str
    llm_id: Optional[str] = None  # optional override

class ChatResponse(BaseModel):
    output: str
    raw: Optional[Dict[str, Any]] = None

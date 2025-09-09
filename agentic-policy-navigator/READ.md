# Policy Navigator — Agentic RAG (React + FastAPI + aiXplain)

**Goal:** Upload policy docs → extract text with your aiXplain PDFTextExtractor tool → index into your existing `policy-documents-index` → ask questions through your **Executive Order Retrieval Pipeline** to get answers with citations/snippets.

## Prereqs
- Python 3.10+
- Node 18+
- An aiXplain API key in `.env` as `AIXPLAIN_API_KEY` (per docs).  

## Setup

```bash
# Backend
cd backend
cp .env.example .env
# paste your team key into .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

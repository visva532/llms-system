import sys
import os
import requests
import ollama
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from urllib.parse import quote_plus

# =========================
# Path setup for imports
# =========================
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loader.chunker import chunk_document
from retriever.pinecone_store import query_chunks

# =========================
# Environment variables
# =========================
TEAM_TOKEN = os.getenv("TEAM_TOKEN", "hackrx2025securetoken")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
DEFAULT_POLICY_URL = os.getenv("DEFAULT_POLICY_URL")

# =========================
# FastAPI app
# =========================
app = FastAPI(
    title="HackRx API",
    version="1.0",
    description="LLM-powered Intelligent Query–Retrieval System for HackRx 6.0"
)

# =========================
# Health check & root
# =========================
@app.get("/")
def root():
    return {"status": "ok", "message": "HackRx API is running on Render"}

@app.get("/health")
@app.get("/healthz")
def health():
    return {"status": "ok"}

# =========================
# Request Model
# =========================
class HackRxRequest(BaseModel):
    documents: list[str]
    questions: list[str]

# =========================
# Startup event - preload default policy
# =========================
@app.on_event("startup")
def preload_default():
    if DEFAULT_POLICY_URL:
        pdf_path = "default.pdf"
        try:
            print(f"📥 Downloading default policy from {DEFAULT_POLICY_URL} ...")
            r = requests.get(DEFAULT_POLICY_URL, timeout=60)
            r.raise_for_status()
            with open(pdf_path, "wb") as f:
                f.write(r.content)
            chunk_document(pdf_path, namespace="default_policy")
            print("✅ Default policy loaded successfully.")
        except Exception as e:
            print(f"⚠ Failed to preload default policy: {e}")

# =========================
# Main endpoint
# =========================
@app.post("/hackrx/run")
async def hackrx_run(req: Request, payload: HackRxRequest):
    # Authorization
    if req.headers.get("Authorization") != f"Bearer {TEAM_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Process all provided documents
    for doc_url in payload.documents:
        pdf_path = "temp.pdf"
        try:
            r = requests.get(doc_url, timeout=60)
            r.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download {doc_url}: {e}")

        with open(pdf_path, "wb") as f:
            f.write(r.content)

        # Safe namespace for Pinecone
        safe_namespace = quote_plus(doc_url)
        chunk_document(pdf_path, namespace=safe_namespace)

    # Answer questions
    answers = []
    for q in payload.questions:
        top_chunks = []
        for doc_url in payload.documents:
            safe_namespace = quote_plus(doc_url)
            top_chunks.extend(query_chunks(q, top_k=3, namespace=safe_namespace))

        # Create context
        context = "\n".join([m["metadata"]["text"] for m in top_chunks])

        # Create prompt
        prompt = (
            "Answer based only on the policy document. "
            "Include exact sentence + page number.\n\n"
            f"{context}\n\n"
            f"Question: {q}\nAnswer:"
        )

        # Generate answer
        try:
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": "You are a precise insurance assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            answer_text = response.get("message", {}).get("content", "").strip()
        except Exception as e:
            answer_text = f"⚠ Error generating answer: {e}"

        answers.append({
            "question": q,
            "answer": answer_text,
            "source": context
        })

    return {"answers": answers}

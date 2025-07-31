import os
import requests
import ollama
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from loader.chunker import chunk_document
from retriever.pinecone_store import query_chunks

# Environment variables
TEAM_TOKEN = os.getenv("TEAM_TOKEN", "hackrx2025securetoken")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
DEFAULT_POLICY_URL = os.getenv("DEFAULT_POLICY_URL")

app = FastAPI(title="HackRx API", version="1.0")

# ✅ Root endpoint for Railway healthcheck
@app.get("/")
def root():
    return {"status": "ok", "message": "HackRx API is running on Railway"}

# ✅ Dedicated healthcheck endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

class HackRxRequest(BaseModel):
    documents: list[str]
    questions: list[str]

@app.on_event("startup")
def preload_default():
    """Preload a default policy document if DEFAULT_POLICY_URL is set."""
    if DEFAULT_POLICY_URL:
        pdf_path = "default.pdf"
        try:
            r = requests.get(DEFAULT_POLICY_URL, timeout=30)
            r.raise_for_status()
            with open(pdf_path, "wb") as f:
                f.write(r.content)
            chunk_document(pdf_path, namespace="default_policy")
            print("✅ Default policy loaded successfully.")
        except Exception as e:
            print(f"⚠ Failed to preload default policy: {e}")

@app.post("/hackrx/run")
async def hackrx_run(req: Request, payload: HackRxRequest):
    """Process policy documents and answer questions."""
    # Authentication
    if req.headers.get("Authorization") != f"Bearer {TEAM_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Process documents
    for doc_url in payload.documents:
        pdf_path = "temp.pdf"
        r = requests.get(doc_url)
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to download: {doc_url}")
        with open(pdf_path, "wb") as f:
            f.write(r.content)
        chunk_document(pdf_path, namespace=doc_url)

    # Answer questions
    answers = []
    for q in payload.questions:
        top_chunks = []
        for doc_url in payload.documents:
            top_chunks.extend(query_chunks(q, top_k=3, namespace=doc_url))

        context = "\n".join([m["metadata"]["text"] for m in top_chunks])

        prompt = (
            f"Answer based only on the policy document. "
            f"Include exact sentence + page number.\n\n{context}\n\n"
            f"Question: {q}\nAnswer:"
        )

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise insurance assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        answers.append({
            "question": q,
            "answer": response["message"]["content"].strip(),
            "source": context
        })

    return {"answers": answers}

# ✅ Proper Railway entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))  # ✅ Fixed $PORT issue
    )

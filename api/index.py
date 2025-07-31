from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mangum import Mangum

app = FastAPI()

@app.get("/")
def home():
    return {"message": "HackRx 6.0 LLM API running on Vercel"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    # For now, just echo back the request payload
    return JSONResponse(content={"received": data})

# Adapter for Vercel serverless
handler = Mangum(app)

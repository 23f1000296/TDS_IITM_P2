from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from agent import run_agent
from dotenv import load_dotenv
import uvicorn
import os
import time
from shared_store import url_time, BASE64_STORE

# Load environment variables
load_dotenv()

EMAIL = os.getenv("EMAIL")
SECRET = os.getenv("SECRET")

if not SECRET:
    raise RuntimeError("SECRET environment variable not set")

app = FastAPI(title="IITM TDS Project 2 API")

# CORS (safe default for API usage)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()

# -------------------------
# Root endpoint (IMPORTANT)
# -------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "service": "IITM TDS Project 2"
    }

# -------------------------
# Health check
# -------------------------
@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME)
    }

# -------------------------
# Main solve endpoint
# -------------------------
@app.post("/solve")
async def solve(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    url = data.get("url")
    secret = data.get("secret")

    if not url or not secret:
        raise HTTPException(status_code=400, detail="Missing url or secret")

    if secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # Reset shared state
    url_time.clear()
    BASE64_STORE.clear()

    # Set runtime variables
    os.environ["url"] = url
    os.environ["offset"] = "0"
    url_time[url] = time.time()

    # Run agent in background
    background_tasks.add_task(run_agent, url)

    return JSONResponse(
        status_code=200,
        content={"status": "ok", "message": "Task started"}
    )

# -------------------------
# Local / container run
# -------------------------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 7860))
    )

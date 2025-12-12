import os
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, ValidationError
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from quiz_solver import QuizSolver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("quiz-api")

# Load configuration from environment
SECRET_KEY = os.getenv("SECRET_KEY", "")
STUDENT_EMAIL = os.getenv("STUDENT_EMAIL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if not SECRET_KEY or not STUDENT_EMAIL:
    logger.warning("SECRET_KEY or STUDENT_EMAIL not set in environment!")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set in environment!")

# Global solver instance
solver: Optional[QuizSolver] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global solver
    solver = QuizSolver(
        email=STUDENT_EMAIL,
        secret=SECRET_KEY,
        openai_api_key=OPENAI_API_KEY
    )
    await solver.initialize()
    logger.info("Quiz solver initialized")
    yield
    await solver.cleanup()
    logger.info("Quiz solver cleaned up")

app = FastAPI(
    title="LLM Quiz Solver API",
    lifespan=lifespan
)

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str
    metadata: Optional[Dict[str, Any]] = None

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "status": "error",
            "message": "Invalid request payload",
            "details": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "message": "Internal server error"}
    )

async def process_quiz_chain(quiz_url: str):
    """Process a quiz and any subsequent quizzes in the chain"""
    start_time = datetime.now()
    try:
        await solver.solve_quiz_chain(quiz_url, start_time)
    except Exception as e:
        logger.exception(f"Error processing quiz chain: {e}")

@app.post("/project2", status_code=200)
async def receive_quiz(request: Request, background_tasks: BackgroundTasks):
    """
    Main endpoint to receive quiz tasks
    - Validates secret (403 if wrong)
    - Returns 400 for invalid JSON
    - Returns 200 and starts processing
    """
    try:
        payload_json = await request.json()
    except Exception as e:
        logger.warning(f"Malformed JSON in request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON"
        )

    # Validate payload structure
    try:
        quiz_req = QuizRequest(**payload_json)
    except ValidationError as ve:
        logger.warning(f"Payload validation failed: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )

    # Verify secret
    if quiz_req.secret != SECRET_KEY:
        logger.warning(f"Secret verification failed for {quiz_req.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: invalid secret"
        )

    # Schedule background processing
    background_tasks.add_task(process_quiz_chain, quiz_req.url)
    
    logger.info(f"Accepted quiz request from {quiz_req.email} for {quiz_req.url}")
    
    return {
        "status": "processing",
        "message": "Quiz received and being processed"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "solver_ready": solver is not None
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LLM Quiz Solver API",
        "version": "1.0",
        "endpoints": {
            "quiz": "POST /project2",
            "health": "GET /health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    # Hugging Face uses port 7860 by default
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from engine import run_quiz

SECRET = "Alpha"

app = FastAPI(title="TDS Project 2 – Extreme++ Solver")

class Request(BaseModel):
    email: str
    secret: str
    url: str

@app.post("/quiz")
def quiz(req: Request):
    if req.secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    return run_quiz(req.url, req.email, req.secret)

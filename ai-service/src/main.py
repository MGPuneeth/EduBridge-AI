import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.routers import questions, scoring, careers

load_dotenv()

app = FastAPI(title="EduBridge AI - AI Service")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Set either GEMINI_API_KEY or GROQ_API_KEY before starting the AI service.")

@app.get("/health")
async def health_check():
    providers = []
    if os.getenv("GEMINI_API_KEY"):
        providers.append("gemini-2.5-flash")
    if os.getenv("GROQ_API_KEY"):
        providers.append(os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))

    return {"status": "ok", "models": providers}

app.include_router(questions.router, prefix="/api", tags=["questions"])
app.include_router(scoring.router, prefix="/api", tags=["scoring"])
app.include_router(careers.router, prefix="/api", tags=["careers"])

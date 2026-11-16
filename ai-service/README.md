# EduBridge AI - AI Service

Python FastAPI service for question generation, assessment scoring, career recommendations, skill-gap analysis, and learning paths. Questions use Gemini with Groq as a fallback; learning paths use Ollama with a deterministic fallback.

## Getting Started

1. Copy `.env.example` to `.env`. Configure `GEMINI_API_KEY` and/or `GROQ_API_KEY` for AI-generated assessment questions, and configure `OLLAMA_BASE_URL` and `OLLAMA_MODEL` for AI-generated learning paths.
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Run the server: `uvicorn src.main:app --reload --port 8000`

## Skill Gap Agent

`POST /api/skill-gap-agent` provides a deterministic agent-style skill gap analysis using assessment scores, recommended roles, career requirements, and market trend domains.

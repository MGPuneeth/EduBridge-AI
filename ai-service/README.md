# EduBridge AI - AI Service

Python FastAPI service using local Ollama models for question generation, scoring support, and career reasoning.

## Getting Started

1. Copy `.env.example` to `.env` and configure `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `OLLAMA_FALLBACK_MODEL`.
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Run the server: `uvicorn src.main:app --reload --port 8000`

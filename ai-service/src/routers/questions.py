import json
import random
import re
from typing import List
from fastapi import APIRouter, HTTPException
import os
from pydantic import BaseModel
import google.generativeai as genai
import httpx

router = APIRouter()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def get_gemini_model():
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    return genai.GenerativeModel('gemini-2.5-flash')

class GenerateQuestionsRequest(BaseModel):
    domain: str
    skills: List[str]

def fallback_questions(skill: str, difficulty: str, domain: str) -> List[dict]:
    topic = skill or domain.replace("_", " ").title()
    templates = {
        "beginner": [
            ("Which option best describes a variable?", "A"),
            ("What is the main purpose of a function?", "B"),
            ("Which value usually represents a true/false condition?", "C"),
            ("What does this code print?\n```javascript\nconst total = 2 + 3;\nconsole.log(total);\n```", "D"),
            ("Which practice makes code easier to read?", "A"),
            ("What is the purpose of comments in code?", "B"),
        ],
        "intermediate": [
            ("What is the most likely issue in this code?\n```javascript\nconst items = [1, 2, 3];\nitems.map(item => item * 2);\nconsole.log(result);\n```", "C"),
            ("When should you split logic into a reusable function?", "A"),
            ("What is a common reason to validate input before processing it?", "D"),
            ("Which approach is best when debugging a failing feature?", "B"),
            ("Why are meaningful error messages useful?", "A"),
            ("What is the practical benefit of writing small tests?", "C"),
        ],
        "expert": [
            ("What trade-off matters most when caching frequently requested data?", "B"),
            ("Which design choice improves maintainability in a growing codebase?", "A"),
            ("What is the main risk of tightly coupling modules?", "D"),
            ("In system design, why is observability important?", "C"),
            ("What should guide performance optimization decisions?", "B"),
            ("Which strategy best handles partial failure in distributed systems?", "A"),
        ],
    }

    options = {
        "A": "The option that best fits the engineering principle",
        "B": "A partially correct but incomplete choice",
        "C": "A common misconception",
        "D": "An unrelated implementation detail",
    }

    questions = []
    for idx, (question, correct) in enumerate(templates[difficulty], start=1):
        question_options = options.copy()
        if correct == "B":
            question_options["B"], question_options["A"] = question_options["A"], question_options["B"]
        elif correct == "C":
            question_options["C"], question_options["A"] = question_options["A"], question_options["C"]
        elif correct == "D":
            question_options["D"], question_options["A"] = question_options["A"], question_options["D"]

        questions.append({
            "question": f"{question}\n\nContext: {topic}",
            "options": question_options,
            "correct_answer": correct,
            "explanation": "This fallback question is used when the Gemini API quota is exhausted.",
            "skill": topic,
            "difficulty": difficulty
        })

    return questions

def parse_questions(content: str) -> List[dict]:
    content = content.strip()

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    match = re.search(r"\[[\s\S]*\]", content)
    if match:
        content = match.group(0)

    questions = json.loads(content)
    if isinstance(questions, list):
        return questions

    return []

async def generate_with_groq(prompt: str, difficulty: str) -> List[dict]:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Return only valid JSON. Do not include markdown outside JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_completion_tokens": 4096,
                },
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        questions = parse_questions(content)
        if questions:
            print(f"Generated {difficulty} questions using Groq model {GROQ_MODEL}.")
            return questions[:6]
    except Exception as e:
        print(f"Error generating {difficulty} questions with Groq: {str(e)}")

    return []

async def generate_questions_for_difficulty(skill: str, difficulty: str, domain: str) -> List[dict]:
    prompt = f"""You are a technical assessment expert. Generate exactly 6 multiple-choice questions.

Skill to test: {skill}
Difficulty: {difficulty}
Domain: {domain}

Difficulty definitions:
- beginner: basic syntax, definitions, simple usage
- intermediate: practical application, debugging, common patterns
- expert: system design, optimization, architectural trade-offs

Rules:
- Each question has exactly 4 options: A, B, C, D
- Exactly one correct answer
- Questions must be practical, not trivia
- If a question or option contains code, wrap the code in fenced markdown code blocks
- Return ONLY a valid JSON array, no markdown, no explanation

Format:
[
  {{
    "question": "...",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct_answer": "A",
    "explanation": "Brief explanation of why this is correct",
    "skill": "{skill}",
    "difficulty": "{difficulty}"
  }}
]"""

    for attempt in range(2):
        try:
            model = get_gemini_model()
            response = await model.generate_content_async(prompt)
            questions = parse_questions(response.text)
            if questions:
                return questions[:6]
        except Exception as e:
            error_text = str(e)
            print(f"Error generating {difficulty} questions (attempt {attempt + 1}): {error_text}")
            if "429" in error_text or "quota" in error_text.lower():
                groq_questions = await generate_with_groq(prompt, difficulty)
                if groq_questions:
                    return groq_questions
                return fallback_questions(skill, difficulty, domain)

    groq_questions = await generate_with_groq(prompt, difficulty)
    if groq_questions:
        return groq_questions

    return fallback_questions(skill, difficulty, domain)

@router.post("/generate-questions")
async def generate_questions(request: GenerateQuestionsRequest):
    skill_str = ", ".join(request.skills) if request.skills else "general concepts"
    
    results = []
    for difficulty in ["beginner", "intermediate", "expert"]:
        results.append(await generate_questions_for_difficulty(skill_str, difficulty, request.domain))
    
    all_questions = []
    for res in results:
        if isinstance(res, list):
            all_questions.extend(res)
            
    # Shuffle to interleave the difficulty levels randomly
    random.shuffle(all_questions)
    
    if not all_questions:
        raise HTTPException(status_code=500, detail="Failed to generate questions. Ensure GEMINI_API_KEY is valid.")
        
    return {
        "questions": all_questions,
        "total": len(all_questions)
    }

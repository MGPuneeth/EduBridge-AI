import asyncio
import json
import random
import re
import os
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai

router = APIRouter()
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "90"))

def get_gemini_client():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
        content = re.sub(r"\s*```$", "", content)

    match = re.search(r"\[[\s\S]*\]", content)
    if match:
        content = match.group(0)

    try:
        questions = json.loads(content)
        if isinstance(questions, list):
            return questions
    except json.JSONDecodeError:
        print("Failed to decode JSON from Gemini response.")
        
    return []

from google.genai import types # Add this to your imports at the top

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
            client = get_gemini_client()
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    # Forcing JSON output natively speeds up generation and prevents markdown formatting issues
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7, 
                    )
                ),
                timeout=GEMINI_TIMEOUT_SECONDS,
            )
            
            questions = parse_questions(response.text)
            if questions:
                return questions[:6]
                
        except Exception as e:
            # Using repr(e) ensures we actually see the error name, even if the message is empty (like TimeoutError)
            print(f"Error generating {difficulty} questions (attempt {attempt + 1}): {repr(e)}")
            
    print(f"Falling back to local templates for {difficulty} level due to API failure.")
    return fallback_questions(skill, difficulty, domain)
@router.post("/generate-questions")
async def generate_questions(request: GenerateQuestionsRequest):
    skill_str = ", ".join(request.skills) if request.skills else "general concepts"
    
    results = await asyncio.gather(
        *[
            generate_questions_for_difficulty(skill_str, difficulty, request.domain)
            for difficulty in ["beginner", "intermediate", "expert"]
        ]
    )
    
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
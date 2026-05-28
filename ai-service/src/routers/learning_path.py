import os
import json
import re
import httpx
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

RESOURCE_LIBRARY = [
    {"skill": "python", "title": "Python for Everybody", "provider": "freeCodeCamp", "type": "Free course", "level": "Beginner", "durationHours": 8, "url": "https://www.freecodecamp.org/news/learn-python-free-python-courses-for-beginners/", "topics": ["syntax", "functions", "files", "problem solving"]},
    {"skill": "javascript", "title": "JavaScript Guide", "provider": "MDN Web Docs", "type": "Documentation", "level": "Beginner", "durationHours": 8, "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "topics": ["functions", "objects", "DOM", "async JavaScript"]},
    {"skill": "typescript", "title": "TypeScript Handbook", "provider": "TypeScript", "type": "Documentation", "level": "Intermediate", "durationHours": 6, "url": "https://www.typescriptlang.org/docs/handbook/intro.html", "topics": ["types", "interfaces", "generics", "narrowing"]},
    {"skill": "react", "title": "React Learn", "provider": "React", "type": "Documentation", "level": "Beginner", "durationHours": 8, "url": "https://react.dev/learn", "topics": ["components", "state", "props", "effects"]},
    {"skill": "html css", "title": "Responsive Web Design", "provider": "freeCodeCamp", "type": "Free course", "level": "Beginner", "durationHours": 10, "url": "https://www.freecodecamp.org/learn/2022/responsive-web-design/", "topics": ["semantic HTML", "CSS layout", "accessibility", "responsive design"]},
    {"skill": "accessibility", "title": "Accessibility Learning Path", "provider": "MDN Web Docs", "type": "Guide", "level": "Beginner", "durationHours": 5, "url": "https://developer.mozilla.org/en-US/docs/Learn/Accessibility", "topics": ["semantic structure", "keyboard support", "labels", "contrast"]},
    {"skill": "node.js", "title": "Node.js Learn", "provider": "Node.js", "type": "Documentation", "level": "Beginner", "durationHours": 6, "url": "https://nodejs.org/en/learn", "topics": ["runtime", "modules", "HTTP", "npm"]},
    {"skill": "sql", "title": "SQLBolt Interactive SQL Lessons", "provider": "SQLBolt", "type": "Interactive course", "level": "Beginner", "durationHours": 4, "url": "https://sqlbolt.com/", "topics": ["SELECT", "joins", "GROUP BY", "filters"]},
    {"skill": "machine learning", "title": "Machine Learning Crash Course", "provider": "Google Developers", "type": "Free course", "level": "Intermediate", "durationHours": 12, "url": "https://developers.google.com/machine-learning/crash-course", "topics": ["supervised learning", "model evaluation", "feature engineering"]},
    {"skill": "docker", "title": "Docker Getting Started", "provider": "Docker Docs", "type": "Documentation", "level": "Beginner", "durationHours": 4, "url": "https://docs.docker.com/get-started/", "topics": ["images", "containers", "Dockerfile", "volumes"]},
    {"skill": "cloud", "title": "AWS Cloud Practitioner Essentials", "provider": "AWS Skill Builder", "type": "Free course", "level": "Beginner", "durationHours": 6, "url": "https://skillbuilder.aws/learn", "topics": ["compute", "storage", "networking", "security"]},
    {"skill": "databases", "title": "MongoDB University Basics", "provider": "MongoDB University", "type": "Free course", "level": "Beginner", "durationHours": 6, "url": "https://learn.mongodb.com/", "topics": ["documents", "indexes", "queries", "schema design"]},
    {"skill": "api design", "title": "REST API Design Guidance", "provider": "Microsoft Learn", "type": "Guide", "level": "Intermediate", "durationHours": 4, "url": "https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design", "topics": ["resources", "status codes", "versioning", "pagination"]},
    {"skill": "statistics", "title": "Introductory Statistics", "provider": "OpenStax", "type": "Free textbook", "level": "Beginner", "durationHours": 8, "url": "https://openstax.org/details/books/introductory-statistics", "topics": ["probability", "distributions", "hypothesis testing", "correlation"]},
    {"skill": "linux", "title": "Command Line for Beginners", "provider": "Ubuntu", "type": "Tutorial", "level": "Beginner", "durationHours": 4, "url": "https://ubuntu.com/tutorials/command-line-for-beginners", "topics": ["files", "permissions", "processes", "logs"]},
    {"skill": "ci cd", "title": "GitHub Actions Quickstart", "provider": "GitHub Docs", "type": "Documentation", "level": "Intermediate", "durationHours": 4, "url": "https://docs.github.com/en/actions/writing-workflows/quickstart", "topics": ["workflow files", "jobs", "triggers", "test automation"]},
    {"skill": "data visualization", "title": "Data Visualization Curriculum", "provider": "freeCodeCamp", "type": "Free course", "level": "Beginner", "durationHours": 10, "url": "https://www.freecodecamp.org/learn/data-visualization/", "topics": ["charts", "dashboards", "visual storytelling", "D3 basics"]},
    {"skill": "excel", "title": "Excel for Beginners", "provider": "Microsoft Support", "type": "Guide", "level": "Beginner", "durationHours": 4, "url": "https://support.microsoft.com/en-us/excel", "topics": ["formulas", "tables", "charts", "pivot tables"]},
]


class MissingSkill(BaseModel):
    skill: str
    userScore: float
    requiredScore: float
    gap: float
    sourceRoles: List[str] = []
    marketRelevance: float = 50
    priority: str = "medium"


class RoleGapSummary(BaseModel):
    role: str
    domain: str
    averageGap: float
    readinessScore: float


class LearningPathRequest(BaseModel):
    assessmentDomain: Optional[str] = "general"
    readinessScore: Optional[float] = 0
    missingSkills: List[MissingSkill] = []
    roleGapSummary: Optional[List[RoleGapSummary]] = []
    overallGapPercentage: Optional[float] = 0


def normalize(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[/.+#_-]", " ", value)
    value = re.sub(r"[^a-z0-9\s]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def find_resource(skill: str) -> Dict:
    norm = normalize(skill)
    for r in RESOURCE_LIBRARY:
        if normalize(r["skill"]) == norm:
            return r
    for r in RESOURCE_LIBRARY:
        rs = normalize(r["skill"])
        if rs in norm or norm in rs:
            return r
    return {
        "skill": skill,
        "title": f"{skill} free beginner course",
        "provider": "YouTube Search",
        "type": "Free course search",
        "level": "Beginner",
        "durationHours": 4,
        "url": f"https://www.youtube.com/results?search_query={skill.replace(' ', '+')}+free+course+for+beginners",
        "topics": ["core concepts", "guided practice", "project evidence"],
    }


async def call_ollama(prompt: str) -> str:
    """Call Ollama API and return the response text."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 1200,
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except Exception as e:
        print(f"[Ollama error] {e}")
        return ""


def extract_json(text: str) -> Any:
    """Extract JSON from Ollama response text."""
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return None


def build_fallback_modules(skills: List[MissingSkill], target_role: str) -> List[Dict]:
    """Fallback if Ollama fails — generates modules with sensible defaults."""
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_skills = sorted(
        [s for s in skills if s.gap > 0],
        key=lambda s: (priority_order.get(s.priority, 2), -s.gap)
    )[:6]

    modules = []
    for i, gap in enumerate(sorted_skills):
        resource = find_resource(gap.skill)
        modules.append({
            "week": i + 1,
            "skill": gap.skill,
            "priority": gap.priority,
            "currentScore": gap.userScore,
            "targetScore": gap.requiredScore,
            "gap": gap.gap,
            "marketRelevance": gap.marketRelevance,
            "sourceRoles": gap.sourceRoles,
            "title": resource["title"],
            "provider": resource["provider"],
            "type": resource["type"],
            "level": resource["level"],
            "durationHours": resource["durationHours"],
            "url": resource["url"],
            "topics": resource["topics"],
            "practiceTask": f"Complete one hands-on project that demonstrates practical use of {gap.skill}.",
            "checkpoint": f"Raise {gap.skill} from {gap.userScore}% toward {gap.requiredScore}% with a quiz, mini project, or portfolio note.",
            "aiGenerated": False,
        })
    return modules


@router.post("/learning-path-agent")
async def learning_path_agent(request: LearningPathRequest):
    target_role = request.roleGapSummary[0].role if request.roleGapSummary and len(request.roleGapSummary) > 0 else "Recommended career path"

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    top_skills = sorted(
        [s for s in request.missingSkills if s.gap > 0],
        key=lambda s: (priority_order.get(s.priority, 2), -s.gap)
    )[:6]

    if not top_skills:
        return {
            "agentName": "Learning Path Agent",
            "dependsOn": "Skill Gap Agent",
            "assessmentDomain": request.assessmentDomain,
            "targetRole": target_role,
            "readinessScore": request.readinessScore,
            "totalModules": 0,
            "estimatedTotalHours": 0,
            "estimatedWeeks": 0,
            "summary": "No skill gaps found. You are well prepared for your target role!",
            "modules": [],
            "aiGenerated": False,
        }

    skills_summary = "\n".join([
        f"- {s.skill}: current {s.userScore}%, needs {s.requiredScore}%, gap {s.gap}%, priority: {s.priority}, roles: {', '.join(s.sourceRoles[:2])}"
        for s in top_skills
    ])

    prompt = f"""You are an expert career coach and learning path designer for EduBridge AI.

A student has completed a skills assessment and wants to become a {target_role} in the {request.assessmentDomain} domain.
Their current readiness score is {request.readinessScore}%.

Their skill gaps (ordered by priority) are:
{skills_summary}

For each skill gap above, generate a personalized learning module. Return ONLY a valid JSON array with exactly {len(top_skills)} objects. Each object must have these exact fields:
- "skill": the skill name
- "practiceTask": a specific, actionable 1-2 sentence hands-on task the student should complete to practice this skill
- "checkpoint": a specific measurable goal the student should hit before moving to the next module
- "weeklyGoal": a short motivational sentence describing what the student will achieve this week
- "whyImportant": 1 sentence explaining why this skill matters for becoming a {target_role}

Return ONLY the JSON array, no explanation, no markdown, no code blocks."""

    print(f"[LearningPathAgent] Calling Ollama model={OLLAMA_MODEL} for {len(top_skills)} skills...")
    ai_response = await call_ollama(prompt)
    ai_data = extract_json(ai_response) if ai_response else None

    modules = []
    ai_generated = False

    if ai_data and isinstance(ai_data, list) and len(ai_data) > 0:
        print(f"[LearningPathAgent] Ollama returned {len(ai_data)} AI-generated modules")
        ai_generated = True
        for i, gap in enumerate(top_skills):
            resource = find_resource(gap.skill)
            ai_module = ai_data[i] if i < len(ai_data) else {}
            modules.append({
                "week": i + 1,
                "skill": gap.skill,
                "priority": gap.priority,
                "currentScore": gap.userScore,
                "targetScore": gap.requiredScore,
                "gap": gap.gap,
                "marketRelevance": gap.marketRelevance,
                "sourceRoles": gap.sourceRoles,
                "title": resource["title"],
                "provider": resource["provider"],
                "type": resource["type"],
                "level": resource["level"],
                "durationHours": resource["durationHours"],
                "url": resource["url"],
                "topics": resource["topics"],
                "practiceTask": ai_module.get("practiceTask", f"Complete a hands-on project using {gap.skill}."),
                "checkpoint": ai_module.get("checkpoint", f"Raise {gap.skill} from {gap.userScore}% toward {gap.requiredScore}%."),
                "weeklyGoal": ai_module.get("weeklyGoal", f"Build confidence in {gap.skill} through guided practice."),
                "whyImportant": ai_module.get("whyImportant", f"{gap.skill} is essential for becoming a {target_role}."),
                "aiGenerated": True,
            })
    else:
        print(f"[LearningPathAgent] Ollama unavailable or failed — using smart fallback")
        modules = build_fallback_modules(top_skills, target_role)

    estimated_hours = sum(m["durationHours"] for m in modules)

    return {
        "agentName": "Learning Path Agent",
        "dependsOn": "Skill Gap Agent",
        "assessmentDomain": request.assessmentDomain,
        "targetRole": target_role,
        "readinessScore": request.readinessScore,
        "totalModules": len(modules),
        "estimatedTotalHours": estimated_hours,
        "estimatedWeeks": max(1, -(-estimated_hours // 6)),
        "summary": f"Learning Path Agent (AI) created {len(modules)} personalized modules for your journey to {target_role}." if ai_generated else f"Learning Path Agent created {len(modules)} modules based on your skill gaps.",
        "modules": modules,
        "aiGenerated": ai_generated,
    }

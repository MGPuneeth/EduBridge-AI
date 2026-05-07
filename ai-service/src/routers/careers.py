from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional

router = APIRouter()

class CareerDatasetItem(BaseModel):
    role: str
    requiredSkills: Dict[str, float]
    demandScore: float
    description: str

class RecommendCareersRequest(BaseModel):
    skill_scores: Dict[str, float]
    level_per_skill: Dict[str, str]
    overall_level: str
    career_dataset: List[CareerDatasetItem]

def calculate_readiness(score: float) -> str:
    if score >= 80:
        return "Ready to apply"
    elif score >= 60:
        return "Almost ready"
    elif score >= 40:
        return "Some preparation needed"
    else:
        return "Significant preparation needed"

@router.post("/recommend-careers")
async def recommend_careers(request: RecommendCareersRequest):
    recommendations = []
    
    for career in request.career_dataset:
        total_required = sum(career.requiredSkills.values())
        if total_required == 0:
            continue
            
        compatibility_score = 0.0
        skill_gap = []
        
        for skill, req_score in career.requiredSkills.items():
            skill_weight = req_score / total_required
            user_score = request.skill_scores.get(skill, 0.0)
            
            # Contribution
            contribution = min(user_score / req_score, 1.0) * skill_weight * 100 if req_score > 0 else 0
            compatibility_score += contribution
            
            # Skill Gap
            if user_score < req_score:
                skill_gap.append({
                    "skill": skill,
                    "user_score": user_score,
                    "required_score": req_score,
                    "gap": round(req_score - user_score, 2)
                })
                
        # Match bonus
        if request.overall_level in ["advanced", "professional"] and compatibility_score >= 70:
            compatibility_score = min(compatibility_score + 5, 100.0)
            
        compatibility_score = round(compatibility_score, 2)
        
        recommendations.append({
            "role": career.role,
            "compatibility_score": compatibility_score,
            "readiness_label": calculate_readiness(compatibility_score),
            "skill_gap": skill_gap,
            "demand_score": career.demandScore,
            "description": career.description
        })
        
    # Sort descending by score
    recommendations.sort(key=lambda x: x["compatibility_score"], reverse=True)
    
    # Get top 5
    top_5 = recommendations[:5]
    
    # Assign ranks
    for i, rec in enumerate(top_5):
        rec["rank"] = i + 1
        
    top_recommendation = top_5[0]["role"] if top_5 else None
    
    return {
        "recommendations": top_5,
        "top_recommendation": top_recommendation,
        "overall_level": request.overall_level
    }

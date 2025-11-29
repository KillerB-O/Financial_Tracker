from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime,timezone

from ....db.session import get_db
from ....db.models.user import User
from .auth import get_current_user
from ....core.recommendation_engine import FinancialRecommender
from ....schemas.recommendation import (
    RecommendationResponse, HealthScoreResponse,
    FinancialGoalCreate, FinancialGoalResponse,
    RecommendationFeedback
)
from ....db.models.recommendation import FinancialGoal, Recommendation

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/health-score", response_model=HealthScoreResponse)
async def get_health_score(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate and return user's financial health score"""
    
    recommender = FinancialRecommender(db, str(current_user.id))
    scores = recommender.calculate_health_score()
    
    # Get profile for behavioral type
    profile = recommender._get_or_create_profile()
    
    # Count pending recommendations
    rec_count = db.query(Recommendation).filter(
        Recommendation.user_id == str(current_user.id),
        Recommendation.status == "pending"
    ).count()
    
    return {
        **scores,
        "behavioral_type": profile.behavioral_type,
        "recommendations_count": rec_count
    }


@router.get("", response_model=List[RecommendationResponse])
async def get_recommendations(
    regenerate: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all recommendations for current user"""
    
    if regenerate:
        # Generate fresh recommendations
        recommender = FinancialRecommender(db, str(current_user.id))
        
        # Generate different types of recommendations
        spending_suggestions = recommender.generate_spending_suggestions()
        subscription_suggestions = recommender.generate_subscription_suggestions()
        
        # Save to database
        all_suggestions = spending_suggestions + subscription_suggestions
        for suggestion in all_suggestions:
            db.add(suggestion)
        
        db.commit()
        
        return all_suggestions
    
    # Return existing recommendations
    recommendations = db.query(Recommendation).filter(
        Recommendation.user_id == str(current_user.id),
        Recommendation.status == "pending"
    ).order_by(Recommendation.priority_score.desc()).all()
    
    return recommendations


@router.post("/{recommendation_id}/feedback")
async def provide_feedback(
    recommendation_id: str,
    feedback: RecommendationFeedback,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User provides feedback on a recommendation"""
    
    recommendation = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id,
        Recommendation.user_id == str(current_user.id)
    ).first()
    
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    recommendation.status = feedback.status
    recommendation.responded_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"status": "success", "message": "Feedback recorded"}


@router.post("/goals", response_model=FinancialGoalResponse)
async def create_goal(
    goal: FinancialGoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new financial goal"""
    
    new_goal = FinancialGoal(
        id=str(uuid.uuid4()),
        user_id=str(current_user.id),
        name=goal.name,
        target_amount=goal.target_amount,
        deadline=goal.deadline,
        category=goal.category
    )
    
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)
    
    # Calculate progress percentage
    progress = (new_goal.current_amount / new_goal.target_amount) * 100
    
    return {
        **new_goal.__dict__,
        "progress_percentage": progress
    }


@router.get("/goals", response_model=List[FinancialGoalResponse])
async def get_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all financial goals for current user"""
    
    goals = db.query(FinancialGoal).filter(
        FinancialGoal.user_id == str(current_user.id),
        FinancialGoal.is_active == True
    ).all()
    
    result = []
    for goal in goals:
        progress = (goal.current_amount / goal.target_amount) * 100 if goal.target_amount > 0 else 0
        result.append({
            **goal.__dict__,
            "progress_percentage": progress
        })
    
    return result


@router.get("/goals/{goal_id}/accelerate", response_model=List[RecommendationResponse])
async def accelerate_goal(
    goal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get suggestions to accelerate a specific goal"""
    
    recommender = FinancialRecommender(db, str(current_user.id))
    suggestions = recommender.accelerate_goal_suggestions(goal_id)
    
    return suggestions
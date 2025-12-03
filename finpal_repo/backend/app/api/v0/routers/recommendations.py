from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime,timezone

from ....db.models.sms import SMS,TransactionType
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

@router.get("/debug")
async def debug_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ....db.models.sms import SMS

    user_id = str(current_user.id)
    
    txns = db.query(SMS).filter(SMS.user_id == str(user_id)).all()
    
    categorized = {}
    for t in txns:
        if t.category:
            categorized[t.category] = categorized.get(t.category, 0) + (t.amount or 0)
    
    recommender=FinancialRecommender(db,user_id)

    # Analyze each category
    analysis = []
    for category, user_spending in categorized.items():
        peer_median = recommender.PEER_MEDIANS.get(category, 3000)
        if peer_median == 0:
            continue
            
        excess_ratio = (user_spending / peer_median) - 1
        savings = user_spending - peer_median
        
        # Calculate confidence (simplified check)
        category_txns = [t for t in txns if t.category == category and t.transaction_type == TransactionType.DEBIT]
        confidence = 0.75 if len(category_txns) >= 3 else 0.5
        
        will_suggest = (
            excess_ratio > recommender.EXCESS_SPENDING_THRESHOLD and
            savings > recommender.MIN_SAVINGS_THRESHOLD and
            confidence > recommender.MIN_CONFIDENCE
        )
        
        analysis.append({
            "category": category,
            "your_spending": round(user_spending, 2),
            "peer_median": peer_median,
            "excess_percent": round(excess_ratio * 100, 1),
            "potential_savings": round(savings, 2),
            "confidence": confidence,
            "checks": {
                "excess_ok": excess_ratio > recommender.EXCESS_SPENDING_THRESHOLD,
                "savings_ok": savings > recommender.MIN_SAVINGS_THRESHOLD,
                "confidence_ok": confidence > recommender.MIN_CONFIDENCE
            },
            "will_generate": will_suggest
        })
    
    # Try generating
    print("\n🔍 Generating suggestions in debug endpoint...")
    suggestions = recommender.generate_spending_suggestions()
    print(f"✅ Generated {len(suggestions)} suggestions\n")
    
    return {
        "user_id": user_id,
        "transactions_total": len(txns),
        "categorized_spending": categorized,
        "thresholds": {
            "MIN_SAVINGS_THRESHOLD": recommender.MIN_SAVINGS_THRESHOLD,
            "MIN_CONFIDENCE": recommender.MIN_CONFIDENCE,
            "EXCESS_SPENDING_THRESHOLD": f"{recommender.EXCESS_SPENDING_THRESHOLD * 100}%"
        },
        "peer_medians": recommender.PEER_MEDIANS,
        "analysis": analysis,
        "suggestions_generated": len(suggestions),
        "suggestions": [
            {
                "title": s.title,
                "category": s.category,
                "monthly_savings": s.monthly_savings,
                "confidence": s.confidence_score,
                "priority": s.priority_score
            } for s in suggestions
        ]
    }

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
    user_id=str(current_user.id)
    if regenerate:

        print("   ├─ Regenerating recommendations...")
        
        # Delete old pending recommendations first
        db.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.status == "pending"
        ).delete()
        db.commit()
        
        # Generate fresh recommendations
        recommender = FinancialRecommender(db, user_id)
        
        print("   ├─ Generating spending suggestions...")
        spending_suggestions = recommender.generate_spending_suggestions()
        print(f"   │  └─ Generated {len(spending_suggestions)} spending suggestions")
        
        print("   ├─ Generating subscription suggestions...")
        subscription_suggestions = recommender.generate_subscription_suggestions()
        print(f"   │  └─ Generated {len(subscription_suggestions)} subscription suggestions")
        
        # Save to database
        all_suggestions = spending_suggestions + subscription_suggestions
        if all_suggestions:
            for suggestion in all_suggestions:
                db.add(suggestion)
        
            db.commit()

            for suggestion in all_suggestions:
                db.refresh(suggestion)
        
            return all_suggestions
        else:
            return []
    
    print("   ├─ Checking for existing recommendations...")
    recommendations = db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.status == "pending"
    ).order_by(Recommendation.priority_score.desc()).all()
    
    if not recommendations:
        print("   ├─ ⚠️  No existing recommendations found")
        print("   ├─ 🔄 Auto-generating recommendations...")
        
        # Auto-generate if none exist
        recommender = FinancialRecommender(db, user_id)
        
        spending_suggestions = recommender.generate_spending_suggestions()
        subscription_suggestions = recommender.generate_subscription_suggestions()
        
        all_suggestions = spending_suggestions + subscription_suggestions
        
        if all_suggestions:
            print(f"   ├─ Saving {len(all_suggestions)} auto-generated suggestions...")
            for suggestion in all_suggestions:
                db.add(suggestion)
            
            db.commit()
            
            for suggestion in all_suggestions:
                db.refresh(suggestion)
            
            print(f"   └─ ✅ Returning {len(all_suggestions)} auto-generated suggestions\n")
            return all_suggestions
        else:
            print("   └─ ⚠️  Still no suggestions generated (check thresholds)\n")
            return []
    
    print(f"   └─ ✅ Returning {len(recommendations)} existing recommendations\n")
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
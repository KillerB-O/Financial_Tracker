from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ....db.session import get_db
from ....db.models.user import User
from .auth import get_current_user
from ....core.behavioral_engine import BehavioralEngine
from ....schemas.challenges import (
    ChallengeResponse, NudgeResponse, StreakResponse, ChallengeCreate
)
from ....db.models.challenges import Challenge, Nudge, UserStreak

router = APIRouter(prefix="/challenges", tags=["challenges"])


@router.get("", response_model=List[ChallengeResponse])
async def get_challenges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get active challenges for user"""
    
    challenges = db.query(Challenge).filter(
        Challenge.user_id == str(current_user.id),
        Challenge.status == "active"
    ).all()
    
    result = []
    for c in challenges:
        progress = (c.current_value / c.target_value * 100) if c.target_value > 0 else 0
        result.append({
            **c.__dict__,
            "progress_percentage": min(100, progress)
        })
    
    return result


@router.post("/generate", response_model=List[ChallengeResponse])
async def generate_challenges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate new weekly challenges"""
    
    engine = BehavioralEngine(db, str(current_user.id))
    challenges = engine.generate_weekly_challenges()
    
    result = []
    for c in challenges:
        result.append({
            **c.__dict__,
            "progress_percentage": 0
        })
    
    return result


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's streak and points"""
    
    engine = BehavioralEngine(db, str(current_user.id))
    streak = engine._get_or_create_streak()
    
    return streak


@router.get("/nudges", response_model=List[NudgeResponse])
async def get_nudges(
    unread_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get nudges for user"""
    
    query = db.query(Nudge).filter(Nudge.user_id == str(current_user.id))
    
    if unread_only:
        query = query.filter(Nudge.viewed == False)
    
    nudges = query.order_by(Nudge.sent_at.desc()).limit(10).all()
    
    return nudges


@router.post("/nudges/{nudge_id}/view")
async def mark_nudge_viewed(
    nudge_id: str,
    action_taken: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark nudge as viewed and track response"""
    
    engine = BehavioralEngine(db, str(current_user.id))
    engine.track_nudge_response(nudge_id, action_taken)
    
    return {"status": "success"}
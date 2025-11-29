from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from ....db.session import get_db
from ....db.models.user import User
from ....core.security import  get_password_hash, verify_password
from ....schemas.user import UserRead, UserUpdate, PasswordChange,UserPreferencesResponse,UserPreferencesUpdate
from ....core.helpers.validation_helpers import ValidationHelper
from .auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile
    """
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
    )


@router.put("/me", response_model=UserRead)
async def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update current user's profile
    """
    # Validate email if provided
    if user_update.email and user_update.email != current_user.email:
        if not ValidationHelper.is_valid_email(user_update.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Check if email already exists
        existing_user = db.query(User).filter(
            User.email == user_update.email.lower(),
            User.id != current_user.id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        current_user.email = user_update.email.lower()
    
    # Update full name if provided
    if user_update.full_name is not None:
        sanitized_name = ValidationHelper.sanitize_input(user_update.full_name, max_length=100)
        current_user.full_name = sanitized_name
    
    db.commit()
    db.refresh(current_user)
    
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
    )


@router.post("/me/change-password")
async def change_password(
    password_change: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Change current user's password
    """
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(password_change.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )
    
    # Hash and save new password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.delete("/me")
async def delete_current_user(
    password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete current user's account (requires password confirmation)
    """
    # Verify password before deletion
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Soft delete - deactivate account instead of hard delete
    current_user.is_active = False
    db.commit()
    
    return {"message": "Account deactivated successfully"}


@router.get("/me/stats")
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's statistics (transactions, goals, challenges)
    """
    from ....db.models.sms import SMS
    from ....db.models.recommendation import FinancialGoal, Recommendation
    from ....db.models.challenges import Challenge, UserStreak
    
    # Count transactions
    total_transactions = db.query(SMS).filter(
        SMS.user_id == str(current_user.id)
    ).count()
    
    # Count active goals
    active_goals = db.query(FinancialGoal).filter(
        FinancialGoal.user_id == str(current_user.id),
        FinancialGoal.is_active == True
    ).count()
    
    # Count pending recommendations
    pending_recommendations = db.query(Recommendation).filter(
        Recommendation.user_id == str(current_user.id),
        Recommendation.status == "pending"
    ).count()
    
    # Get streak
    streak = db.query(UserStreak).filter(
        UserStreak.user_id == str(current_user.id)
    ).first()
    
    # Count completed challenges
    completed_challenges = db.query(Challenge).filter(
        Challenge.user_id == str(current_user.id),
        Challenge.status == "completed"
    ).count()
    
    return {
        "total_transactions": total_transactions,
        "active_goals": active_goals,
        "pending_recommendations": pending_recommendations,
        "current_streak": streak.current_streak if streak else 0,
        "total_points": streak.total_points if streak else 0,
        "completed_challenges": completed_challenges,
        "account_created": current_user.created_at,
    }


@router.get("/me/preferences")
async def get_user_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's preferences and settings
    """
    from ....db.models.recommendation import UserFinancialProfile
    
    profile = db.query(UserFinancialProfile).filter(
        UserFinancialProfile.user_id == str(current_user.id)
    ).first()
    
    if not profile:
        return {
            "monthly_income": None,
            "risk_tolerance": 0.5,
            "behavioral_type": None,
            "preferred_categories": [],
        }
    
    return {
        "monthly_income": profile.monthly_income,
        "risk_tolerance": profile.risk_tolerance,
        "behavioral_type": profile.behavioral_type,
        "preferred_categories": profile.preferred_categories or [],
    }


@router.put("/me/preferences", response_model=dict)
async def update_user_preferences(
    preferences: UserPreferencesUpdate,  # <-- Use Pydantic model
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user's financial preferences
    
    Request body:
    {
        "monthly_income": 50000,
        "risk_tolerance": 0.6,
        "preferred_categories": ["food", "transport"]
    }
    """
    from ....db.models.recommendation import UserFinancialProfile
    import uuid
    
    # Get or create profile
    profile = db.query(UserFinancialProfile).filter(
        UserFinancialProfile.user_id == str(current_user.id)
    ).first()
    
    if not profile:
        profile = UserFinancialProfile(
            id=str(uuid.uuid4()),
            user_id=str(current_user.id)
        )
        db.add(profile)
    
    # Update only provided fields
    update_data = preferences.dict(exclude_unset=True)  # Only get fields that were actually sent
    
    for field, value in update_data.items():
        if hasattr(profile, field):
            setattr(profile, field, value)
    
    profile.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(profile)
    
    return {
        "message": "Preferences updated successfully",
        "preferences": {
            "monthly_income": profile.monthly_income,
            "risk_tolerance": profile.risk_tolerance,
            "preferred_categories": profile.preferred_categories or [],
        }
    }


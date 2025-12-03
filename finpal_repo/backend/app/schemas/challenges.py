from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ChallengeType(str, Enum):
    SPENDING_LIMIT = "spending_limit"
    SAVING_GOAL = "saving_goal"
    NO_SPEND_DAY = "no_spend_day"
    CATEGORY_LIMIT = "category_limit"
    STREAK_BUILDER = "streak_builder"


class ChallengeCreate(BaseModel):
    type: ChallengeType
    category: Optional[str] = None
    target_value: float
    duration_days: int = 7


class ChallengeResponse(BaseModel):
    id: str
    type: str
    title: str
    description: str
    target_value: float
    current_value: float
    progress_percentage: float
    start_date: datetime
    end_date: datetime
    points_reward: int
    status: str
    
    class Config:
        from_attributes = True


class NudgeResponse(BaseModel):
    id: str
    type: str
    message: str
    action_prompt: Optional[str]
    sent_at: datetime
    
    class Config:
        from_attributes = True


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    total_points: int
    challenges_completed: int
    recommendations_accepted: int

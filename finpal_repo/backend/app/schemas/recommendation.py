from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RecommendationType(str, Enum):
    SPENDING_OPTIMIZATION = "spending_optimization"
    GOAL_ACCELERATION = "goal_acceleration"
    SUBSCRIPTION_OPTIMIZATION = "subscription_optimization"
    BILL_OPTIMIZATION = "bill_optimization"


class RecommendationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DISMISSED = "dismissed"


class FinancialGoalCreate(BaseModel):
    name: str
    target_amount: float
    deadline: Optional[datetime] = None
    category: Optional[str] = None


class FinancialGoalResponse(BaseModel):
    id: str
    user_id: str
    name: str
    target_amount: float
    current_amount: float
    deadline: Optional[datetime]
    category: Optional[str]
    is_active: bool
    progress_percentage: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    id: str
    user_id: str
    type: str
    category: Optional[str]
    title: str
    description: str
    monthly_savings: float
    annual_savings: float
    goal_impact_percentage: Optional[float]
    confidence_score: float
    priority_score: float
    status: str
    shown_at: datetime
    calculation_data: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class RecommendationFeedback(BaseModel):
    recommendation_id: str
    status: RecommendationStatus


class HealthScoreResponse(BaseModel):
    overall_score: float
    savings_score: float
    spending_score: float
    stability_score: float
    progress_score: float
    behavioral_type: Optional[str]
    recommendations_count: int

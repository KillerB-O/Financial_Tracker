from sqlalchemy import Column, String, Float, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime,timezone
from ..base import Base


class FinancialGoal(Base):
    __tablename__ = "financial_goals"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    deadline = Column(DateTime, nullable=True)
    category = Column(String, nullable=True)  # vacation, emergency, car, etc.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class Recommendation(Base):
    __tablename__ = "recommendations"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Recommendation details
    type = Column(String, nullable=False)  # spending_optimization, goal_acceleration, etc.
    category = Column(String, nullable=True)  # food, transport, subscriptions, etc.
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    
    # Financial impact
    monthly_savings = Column(Float, nullable=False)
    annual_savings = Column(Float, nullable=False)
    goal_impact_percentage = Column(Float, nullable=True)
    
    # Scoring
    confidence_score = Column(Float, nullable=False)
    priority_score = Column(Float, nullable=False)
    
    # User interaction
    status = Column(String, default="pending")  # pending, accepted, rejected, dismissed
    shown_at = Column(DateTime, default=datetime.now(timezone.utc))
    responded_at = Column(DateTime, nullable=True)
    
    # Metadata
    calculation_data = Column(JSON, nullable=True)  # Store calculation details
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class UserFinancialProfile(Base):
    __tablename__ = "user_financial_profiles"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Financial health scores
    health_score = Column(Float, default=0.0)
    savings_score = Column(Float, default=0.0)
    spending_score = Column(Float, default=0.0)
    stability_score = Column(Float, default=0.0)
    progress_score = Column(Float, default=0.0)
    
    # Profile characteristics
    monthly_income = Column(Float, nullable=True)
    risk_tolerance = Column(Float, default=0.5)  # 0 to 1
    behavioral_type = Column(String, nullable=True)  # planner, spender, avoider, optimizer
    
    # Preferences
    preferred_categories = Column(JSON, default=list)  # Categories user wants to optimize
    
    updated_at = Column(DateTime, default=datetime.now(timezone.utc) ,onupdate=datetime.now(timezone.utc))

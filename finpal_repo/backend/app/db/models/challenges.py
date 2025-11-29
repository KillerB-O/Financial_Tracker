from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer, JSON, ForeignKey, Text
from datetime import datetime,timezone
from ..base import Base


class Challenge(Base):
    """Weekly/Monthly financial challenges for habit building"""
    __tablename__ = "challenges"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Challenge details
    type = Column(String, nullable=False)  # spending_limit, saving_goal, no_spend_day, etc.
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=True)  # Which category to focus on
    
    # Challenge parameters
    target_value = Column(Float, nullable=False)  # e.g., spend < 5000
    current_value = Column(Float, default=0.0)
    
    # Duration
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Gamification
    points_reward = Column(Integer, default=100)
    streak_multiplier = Column(Float, default=1.0)
    
    # Status
    status = Column(String, default="active")  # active, completed, failed, abandoned
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class Nudge(Base):
    """Behavioral nudges using reinforcement learning"""
    __tablename__ = "nudges"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Nudge content
    type = Column(String, nullable=False)  # reminder, warning, encouragement, tip
    message = Column(Text, nullable=False)
    action_prompt = Column(String, nullable=True)  # CTA text
    
    # Timing optimization (RL)
    sent_at = Column(DateTime, default=datetime.utcnow)
    optimal_time = Column(String, nullable=True)  # morning, afternoon, evening
    
    # User state when nudge was sent
    user_state = Column(JSON, nullable=True)  # Financial health, time of month, recent behavior
    
    # Response tracking
    viewed = Column(Boolean, default=False)
    viewed_at = Column(DateTime, nullable=True)
    action_taken = Column(Boolean, default=False)
    action_taken_at = Column(DateTime, nullable=True)
    
    # RL reward calculation
    engagement_score = Column(Float, default=0.0)
    improvement_score = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class UserStreak(Base):
    """Track user's habit streaks"""
    __tablename__ = "user_streaks"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Streaks
    current_streak = Column(Integer, default=0)  # Days of meeting daily goals
    longest_streak = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    
    # Milestones
    challenges_completed = Column(Integer, default=0)
    recommendations_accepted = Column(Integer, default=0)
    
    last_activity_date = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

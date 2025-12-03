from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, Boolean, ForeignKey, Text,  JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from .user import User
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User

class FinancialGoal(Base):
    __tablename__ = "financial_goals"
    
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # ORM relation to User
    user: Mapped["User"] = relationship("User", back_populates="financial_goals")

    name: Mapped[str] = mapped_column(String, nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    current_amount: Mapped[float] = mapped_column(Float, default=0.0)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)  # vacation, emergency, car, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )

    # ORM relation to User table
    user: Mapped["User"] = relationship("User", back_populates="recommendations")

    # Recommendation details
    type: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Financial impact
    monthly_savings: Mapped[float] = mapped_column(Float, nullable=False)
    annual_savings: Mapped[float] = mapped_column(Float, nullable=False)
    goal_impact_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Scoring
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)

    # User interaction
    status: Mapped[str] = mapped_column(String, default="pending")
    shown_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Metadata
    calculation_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class UserFinancialProfile(Base):
    __tablename__ = "user_financial_profiles"
    
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    # One-to-one relation with User
    user: Mapped["User"] = relationship("User", back_populates="financial_profile")

    # Financial health scores
    health_score: Mapped[float] = mapped_column(Float, default=0.0)
    savings_score: Mapped[float] = mapped_column(Float, default=0.0)
    spending_score: Mapped[float] = mapped_column(Float, default=0.0)
    stability_score: Mapped[float] = mapped_column(Float, default=0.0)
    progress_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Profile characteristics
    monthly_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_tolerance: Mapped[float] = mapped_column(Float, default=0.5)  # 0 to 1
    behavioral_type: Mapped[str | None] = mapped_column(String, nullable=True)  # planner, spender, avoider, optimizer
    
    # Preferences
    preferred_categories: Mapped[list | None] = mapped_column(
        JSON,
        default=list,  # SQLAlchemy will treat this as a callable
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

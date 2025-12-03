
from sqlalchemy import String,Boolean
from sqlalchemy.orm import Mapped,mapped_column,relationship
from datetime import datetime,timezone
import uuid
from app.db.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # only for type hints – does NOT run at import time
    from .recommendation import Recommendation, FinancialGoal, UserFinancialProfile



class User(Base):
    __tablename__="users"
    
  

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )   
    id:Mapped[str]=mapped_column(
        String,primary_key=True,default=lambda:str(uuid.uuid4())
    )
    email:Mapped[str]=mapped_column(String,nullable=False,unique=True,index=True)
    full_name:Mapped[str]=mapped_column(String)
    hashed_password:Mapped[str]=mapped_column(String)
    is_active:Mapped[bool]=mapped_column(Boolean,default=True)

    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation", back_populates="user"
    )

    financial_goals: Mapped[list["FinancialGoal"]] = relationship(
        "FinancialGoal", back_populates="user"
    )

    financial_profile: Mapped["UserFinancialProfile"] = relationship(
        "UserFinancialProfile",
        back_populates="user",
        uselist=False,
    )
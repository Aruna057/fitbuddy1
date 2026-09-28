"""
SQLAlchemy Database Models for FitBuddy.
Defines users and workout_plans tables with relationships and constraints.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def get_utc_now():
    """Returns current UTC datetime timezone-aware or naive UTC for SQLite."""
    return datetime.now(timezone.utc)


class User(Base):
    """
    User model representing registered fitness seekers.
    user_id is a unique alphanumeric identifier chosen by or assigned to the user.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    goal = Column(String(100), nullable=False)
    intensity = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    # Relationship to WorkoutPlan (cascade delete when user is deleted)
    workout_plans = relationship(
        "WorkoutPlan",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(WorkoutPlan.created_at)"
    )

    def to_dict(self):
        """Serialize user model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "age": self.age,
            "weight": self.weight,
            "goal": self.goal,
            "intensity": self.intensity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WorkoutPlan(Base):
    """
    WorkoutPlan model representing generated 7-day plans.
    Preserves original_plan permanently and stores revised plan in updated_plan.
    """
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        String(50),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    original_plan = Column(Text, nullable=False)
    updated_plan = Column(Text, nullable=True, default=None)
    nutrition_tip = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True, default=None)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationship back to User
    user = relationship("User", back_populates="workout_plans")

    # Composite or additional indexes if needed
    __table_args__ = (
        Index("ix_workout_plans_user_created", "user_id", "created_at"),
    )

    def to_dict(self):
        """Serialize workout plan model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "original_plan": self.original_plan,
            "updated_plan": self.updated_plan,
            "nutrition_tip": self.nutrition_tip,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

"""
Pydantic Schemas for FitBuddy.
Provides request validation, data serialization, and response structures.
"""

import re
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class Exercise(BaseModel):
    """Schema for an individual exercise within a workout day."""
    name: str = Field(..., description="Exercise name")
    sets: Optional[Union[int, str]] = Field(default=None, description="Number of sets")
    reps: Optional[Union[int, str]] = Field(default=None, description="Number of reps or target")
    duration: Optional[str] = Field(default=None, description="Duration if time-based (e.g. 30 seconds)")
    rest: Optional[str] = Field(default=None, description="Rest period between sets (e.g. 60s)")


class DayPlan(BaseModel):
    """Schema for a single day of the 7-day workout routine."""
    day: str = Field(..., description="Day label, e.g. Day 1")
    focus: str = Field(..., description="Muscle group or workout focus, e.g. Upper Body")
    warmup: str = Field(..., description="Warm-up routine and mobility work")
    exercises: List[Exercise] = Field(default_factory=list, description="List of scheduled exercises")
    cooldown: str = Field(..., description="Cool-down stretching and recovery work")


class WorkoutPlanStructure(BaseModel):
    """Structured representation of the complete 7-day workout routine."""
    days: List[DayPlan] = Field(..., description="7 daily workout schedules")
    safety_note: Optional[str] = Field(
        default="FitBuddy provides general fitness guidance. Always consult a healthcare professional before beginning any new exercise regimen.",
        description="Important safety reminder"
    )


class UserInput(BaseModel):
    """Validation schema for user fitness profile submission."""
    username: str = Field(..., min_length=2, max_length=50, description="Full name or nickname")
    user_id: str = Field(..., min_length=3, max_length=30, description="Unique alphanumeric identifier")
    age: int = Field(..., ge=13, le=100, description="Age in years (13-100)")
    weight: float = Field(..., gt=20.0, le=300.0, description="Body weight in kilograms (20-300)")
    goal: str = Field(..., min_length=2, max_length=60, description="Fitness goal")
    intensity: str = Field(..., description="Workout intensity level: low, medium, or high")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Username must be at least 2 characters after trimming.")
        return cleaned

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_\-]+$", cleaned):
            raise ValueError("User ID must only contain letters, numbers, underscores, and hyphens.")
        return cleaned

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if len(cleaned) < 2:
            raise ValueError("Goal must be at least 2 characters.")
        return cleaned

    @field_validator("intensity")
    @classmethod
    def validate_intensity(cls, v: str) -> str:
        cleaned = v.strip().lower()
        allowed = ("low", "medium", "high")
        if cleaned not in allowed:
            raise ValueError(f"Intensity must be one of: {', '.join(allowed)}")
        return cleaned


class FeedbackRequest(BaseModel):
    """Validation schema for user feedback to adapt their workout plan."""
    user_id: str = Field(..., min_length=3, max_length=30, description="User identifier")
    feedback: str = Field(..., min_length=3, max_length=1000, description="Feedback or adjustment requests")

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("Feedback must be at least 3 characters long.")
        return cleaned


# ==============================================================================
# API RESPONSE MODELS
# ==============================================================================

class UserResponse(BaseModel):
    id: int
    user_id: str
    username: str
    age: int
    weight: float
    goal: str
    intensity: str
    created_at: Optional[str] = None


class GenerateWorkoutApiResponse(BaseModel):
    success: bool
    user: dict
    workout_plan: dict
    nutrition_tip: str
    message: str


class FeedbackApiResponse(BaseModel):
    success: bool
    user_id: str
    updated_plan: dict
    message: str


class UsersListApiResponse(BaseModel):
    success: bool
    users: List[dict]


class UserDetailApiResponse(BaseModel):
    success: bool
    user: dict
    workout_plan: Optional[dict] = None

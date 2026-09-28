"""
Unit Tests for Pydantic Schemas and Validation.
Verifies boundary checks, data constraints, sanitization, and error handling.
"""

import pytest
from pydantic import ValidationError
from app.schemas import UserInput, FeedbackRequest, Exercise, DayPlan, WorkoutPlanStructure


def test_valid_user_input():
    """Verify that valid user input parses and cleans data successfully."""
    data = {
        "username": "  Jane Doe  ",
        "user_id": "  Jane_D99  ",
        "age": 28,
        "weight": 65.5,
        "goal": "  Muscle Gain  ",
        "intensity": "  Medium  "
    }
    user = UserInput(**data)
    assert user.username == "Jane Doe"
    assert user.user_id == "jane_d99"
    assert user.age == 28
    assert user.weight == 65.5
    assert user.goal == "muscle gain"
    assert user.intensity == "medium"


def test_invalid_age_rejected():
    """Verify that age below 13 or above 100 is strictly rejected."""
    base_data = {
        "username": "Tester",
        "user_id": "test_user",
        "weight": 70.0,
        "goal": "weight loss",
        "intensity": "low"
    }

    # Too young (<13)
    with pytest.raises(ValidationError) as exc:
        UserInput(**{**base_data, "age": 12})
    assert "age" in str(exc.value)

    # Too old (>100)
    with pytest.raises(ValidationError) as exc:
        UserInput(**{**base_data, "age": 105})
    assert "age" in str(exc.value)


def test_invalid_weight_rejected():
    """Verify that non-positive or extreme weights are rejected."""
    base_data = {
        "username": "Tester",
        "user_id": "test_user",
        "age": 30,
        "goal": "endurance",
        "intensity": "medium"
    }

    # Negative or too low
    with pytest.raises(ValidationError) as exc:
        UserInput(**{**base_data, "weight": 0})
    assert "weight" in str(exc.value)

    # Over reasonable limit
    with pytest.raises(ValidationError) as exc:
        UserInput(**{**base_data, "weight": 350.0})
    assert "weight" in str(exc.value)


def test_invalid_intensity_rejected():
    """Verify that intensity outside low/medium/high is rejected."""
    base_data = {
        "username": "Tester",
        "user_id": "test_user",
        "age": 30,
        "weight": 75.0,
        "goal": "strength",
    }

    with pytest.raises(ValidationError) as exc:
        UserInput(**{**base_data, "intensity": "extreme"})
    assert "Intensity must be one of: low, medium, high" in str(exc.value)


def test_invalid_user_id_characters_rejected():
    """Verify that special characters in user_id are rejected."""
    base_data = {
        "username": "Tester",
        "age": 30,
        "weight": 75.0,
        "goal": "strength",
        "intensity": "high"
    }

    with pytest.raises(ValidationError) as exc:
        UserInput(**{**base_data, "user_id": "invalid user!@#"})
    assert "User ID must only contain" in str(exc.value)


def test_valid_feedback():
    """Verify that clean feedback passes validation."""
    fb = FeedbackRequest(user_id="alex_24", feedback="Please add more cardio and stretching.")
    assert fb.user_id == "alex_24"
    assert fb.feedback == "Please add more cardio and stretching."


def test_empty_or_short_feedback_rejected():
    """Verify that empty or whitespace-only feedback is rejected."""
    with pytest.raises(ValidationError):
        FeedbackRequest(user_id="alex_24", feedback="   ")

    with pytest.raises(ValidationError):
        FeedbackRequest(user_id="alex_24", feedback="hi")


def test_workout_plan_structure():
    """Verify that WorkoutPlanStructure correctly validates daily schedules."""
    plan_dict = {
        "days": [
            {
                "day": "Day 1",
                "focus": "Full Body Strength",
                "warmup": "Dynamic stretches for 5 mins",
                "exercises": [
                    {"name": "Squats", "sets": 3, "reps": "12", "duration": None, "rest": "60s"}
                ],
                "cooldown": "Static stretches"
            }
        ],
        "safety_note": "Safety first."
    }
    plan = WorkoutPlanStructure(**plan_dict)
    assert len(plan.days) == 1
    assert plan.days[0].exercises[0].name == "Squats"
    assert plan.safety_note == "Safety first."

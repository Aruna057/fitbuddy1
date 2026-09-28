"""
Utility functions for FitBuddy.
Includes robust JSON extraction, fallback text parsers, sanitization, and safety helpers.
"""

import json
import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("fitbuddy.utils")

FITNESS_SAFETY_DISCLAIMER = (
    "FitBuddy provides general fitness and wellness information and is not a substitute "
    "for professional medical advice. Consult a qualified healthcare professional or fitness "
    "professional if you have an injury, medical condition, or concerns about exercising."
)


def extract_and_parse_json(content: str) -> Optional[Dict[str, Any]]:
    """
    Robustly extract and parse a JSON object from Gemini model responses.
    Handles raw JSON, markdown-wrapped JSON (```json ... ```), and embedded JSON strings.
    """
    if not content:
        return None

    cleaned = content.strip()

    # Try direct parse first
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Extract content inside markdown ```json ... ``` or ``` ... ```
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if code_block_match:
        inside = code_block_match.group(1).strip()
        try:
            data = json.loads(inside)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # Regex search for outer balanced-like curly braces {...}
    brace_match = re.search(r"(\{[\s\S]*\})", cleaned)
    if brace_match:
        candidate = brace_match.group(1).strip()
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.warning(f"Failed to parse matched curly brace content as JSON: {e}")

    return None


def create_fallback_plan(goal: str, intensity: str, note: Optional[str] = None) -> Dict[str, Any]:
    """
    Creates a safe, structured 7-day fallback workout plan in the event of an API outage
    or unparseable response, ensuring the user always gets a high-quality, practical plan.
    """
    default_days = [
        {
            "day": "Day 1",
            "focus": "Full Body Baseline & Mobility",
            "warmup": "5-10 minutes of light dynamic stretching (arm circles, leg swings, torso twists).",
            "exercises": [
                {"name": "Bodyweight Squats", "sets": 3, "reps": "10-12", "duration": None, "rest": "60 seconds"},
                {"name": "Incline or Knee Push-ups", "sets": 3, "reps": "8-10", "duration": None, "rest": "60 seconds"},
                {"name": "Glute Bridges", "sets": 3, "reps": "12-15", "duration": None, "rest": "45 seconds"},
                {"name": "Plank Hold", "sets": 3, "reps": None, "duration": "20-30 seconds", "rest": "45 seconds"}
            ],
            "cooldown": "5 minutes of deep breathing and hamstring/chest static stretches."
        },
        {
            "day": "Day 2",
            "focus": "Low-Impact Cardio & Core",
            "warmup": "3 minutes brisk walking in place and gentle shoulder rolls.",
            "exercises": [
                {"name": "Brisk Walk or Cycling", "sets": 1, "reps": None, "duration": "20-30 minutes", "rest": "As needed"},
                {"name": "Bird-Dog Extensions", "sets": 3, "reps": "10 per side", "duration": None, "rest": "45 seconds"},
                {"name": "Deadbugs", "sets": 3, "reps": "10 per side", "duration": None, "rest": "45 seconds"}
            ],
            "cooldown": "Full body relaxation stretch, focusing on hip flexors."
        },
        {
            "day": "Day 3",
            "focus": "Active Recovery & Gentle Yoga",
            "warmup": "Gentle neck and wrist mobility exercises.",
            "exercises": [
                {"name": "Cat-Cow Flow", "sets": 3, "reps": "10 cycles", "duration": None, "rest": "30 seconds"},
                {"name": "Child's Pose & Downward Dog Stretch", "sets": 3, "reps": None, "duration": "45 seconds each", "rest": "30 seconds"},
                {"name": "Gentle Walking", "sets": 1, "reps": None, "duration": "15-20 minutes", "rest": "Self-paced"}
            ],
            "cooldown": "Mindful breathing and spinal twist stretch."
        },
        {
            "day": "Day 4",
            "focus": "Upper Body & Postural Strength",
            "warmup": "Arm circles, shoulder shrugs, and jumping jacks or step-jacks.",
            "exercises": [
                {"name": "Dumbbell or Resistance Band Rows", "sets": 3, "reps": "10-12", "duration": None, "rest": "60 seconds"},
                {"name": "Overhead Shoulder Press", "sets": 3, "reps": "10-12", "duration": None, "rest": "60 seconds"},
                {"name": "Wall Push-ups or Standard Push-ups", "sets": 3, "reps": "8-12", "duration": None, "rest": "60 seconds"},
                {"name": "Side Plank Hold", "sets": 2, "reps": None, "duration": "15-20 seconds per side", "rest": "45 seconds"}
            ],
            "cooldown": "Upper body static stretch: triceps, shoulders, and chest openers."
        },
        {
            "day": "Day 5",
            "focus": "Lower Body & Balance",
            "warmup": "5 minutes light stationary bike or marching in place with high knees.",
            "exercises": [
                {"name": "Reverse Lunges", "sets": 3, "reps": "8-10 per leg", "duration": None, "rest": "60 seconds"},
                {"name": "Calf Raises", "sets": 3, "reps": "15-20", "duration": None, "rest": "45 seconds"},
                {"name": "Step-ups onto low sturdy step", "sets": 3, "reps": "10 per leg", "duration": None, "rest": "60 seconds"},
                {"name": "Wall Sit", "sets": 3, "reps": None, "duration": "20-30 seconds", "rest": "45 seconds"}
            ],
            "cooldown": "Quad, hamstring, and calf stretching."
        },
        {
            "day": "Day 6",
            "focus": "Cardio Interval & Core Stamina",
            "warmup": "3 minutes dynamic stretching (hip circles, jumping jacks).",
            "exercises": [
                {"name": "Interval Jog/Walk or Step Intervals", "sets": 5, "reps": None, "duration": "1 min work / 1 min walk", "rest": "Self-paced"},
                {"name": "Bicycle Crunches", "sets": 3, "reps": "12 per side", "duration": None, "rest": "45 seconds"},
                {"name": "Mountain Climbers (Controlled pace)", "sets": 3, "reps": "12-15 per leg", "duration": None, "rest": "45 seconds"}
            ],
            "cooldown": "Deep diaphragmatic breathing and child's pose."
        },
        {
            "day": "Day 7",
            "focus": "Full Rest & Recovery",
            "warmup": "Optional gentle 10-minute leisurely outdoor stroll.",
            "exercises": [
                {"name": "Restorative Body Mobility", "sets": 1, "reps": None, "duration": "10 minutes", "rest": "Continuous"},
                {"name": "Hydration and Sleep Optimization", "sets": 1, "reps": None, "duration": "All day", "rest": "Continuous"}
            ],
            "cooldown": "Full body relaxation."
        }
    ]

    return {
        "days": default_days,
        "safety_note": note or FITNESS_SAFETY_DISCLAIMER
    }


def parse_plan_to_dict(plan_data: Any) -> Dict[str, Any]:
    """
    Converts stored plan (string or dict) into a structured dictionary.
    Handles legacy or JSON strings safely.
    """
    if isinstance(plan_data, dict):
        return plan_data

    if isinstance(plan_data, str):
        try:
            parsed = json.loads(plan_data)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            # Try our robust extractor
            parsed = extract_and_parse_json(plan_data)
            if parsed:
                return parsed

    # Fallback default if unparseable
    return create_fallback_plan("general wellness", "medium")

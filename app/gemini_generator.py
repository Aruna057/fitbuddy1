"""
Gemini Workout Generator Module
Leverages the official Google GenAI Python SDK to generate structured 7-day fitness routines.
Enforces fitness safety guidelines, JSON schema adherence, and graceful fallbacks.
"""

import json
import logging
from typing import Optional, Dict, Any
from google import genai
from google.genai import types
from app.config import settings
from app.utils import extract_and_parse_json, create_fallback_plan, FITNESS_SAFETY_DISCLAIMER

logger = logging.getLogger("fitbuddy.gemini_generator")


def build_workout_prompt(
    age: int,
    weight: float,
    goal: str,
    intensity: str,
    preferences: Optional[str] = None
) -> str:
    """Constructs a strict, structured safety-conscious prompt for Gemini."""
    prompt = f"""
You are an expert, certified fitness coach and exercise physiologist.
Create a personalized, evidence-based, 7-day workout routine for a client with the following profile:
- Age: {age} years old
- Body Weight: {weight} kg
- Primary Fitness Goal: {goal}
- Preferred Intensity Level: {intensity} (scale appropriately)
"""
    if preferences:
        prompt += f"- Additional Preferences/Notes: {preferences}\n"

    prompt += f"""
SAFETY AND ETHICAL CONSTRAINTS (STRICT):
1. Do not invent medical diagnoses or provide medical advice.
2. Avoid dangerous, extreme, or high-risk exercise recommendations.
3. Scale exercise complexity, sets, reps, and rest periods strictly according to the specified intensity level ({intensity}).
4. Ensure adequate recovery: include at least 1 or 2 rest/active-recovery days across the 7 days.
5. Provide accessible bodyweight or gym alternatives where appropriate.
6. Consider age ({age}) and weight ({weight} kg) thoughtfully without making unsupported clinical assumptions.
7. Do NOT make unrealistic guarantees or promise exact weight loss or muscle gain numbers.
8. Include a clear safety disclaimer encouraging consultation with a physician or physical therapist.

OUTPUT SPECIFICATION:
You MUST respond with valid JSON adhering EXACTLY to the following schema with all 7 days (Day 1 through Day 7):
{{
  "days": [
    {{
      "day": "Day 1",
      "focus": "e.g. Upper Body Strength or Full Body Mobility",
      "warmup": "Dynamic warm-up description (3-5 minutes)",
      "exercises": [
        {{
          "name": "Exercise Name",
          "sets": 3,
          "reps": "10-12",
          "duration": null,
          "rest": "60 seconds"
        }}
      ],
      "cooldown": "Static stretching and cool-down description (3-5 minutes)"
    }}
  ],
  "safety_note": "{FITNESS_SAFETY_DISCLAIMER}"
}}

Ensure there are exactly 7 distinct day entries in the "days" array (Day 1, Day 2, Day 3, Day 4, Day 5, Day 6, Day 7).
Output ONLY the raw JSON object.
"""
    return prompt.strip()


def generate_workout_gemini(
    age: int,
    weight: float,
    goal: str,
    intensity: str,
    preferences: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a personalized 7-day workout plan using Google Gemini.
    Gracefully handles missing keys, network timeouts, and malformed outputs.
    """
    if not settings.has_gemini_api_key:
        logger.warning("GEMINI_API_KEY is not configured. Serving safe structured fallback plan.")
        fallback = create_fallback_plan(
            goal=goal,
            intensity=intensity,
            note=f"Demo Mode: Google Gemini API key is not configured. {FITNESS_SAFETY_DISCLAIMER}"
        )
        return fallback

    prompt = build_workout_prompt(age, weight, goal, intensity, preferences)

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_WORKOUT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.6,
            ),
        )

        response_text = response.text if hasattr(response, "text") and response.text else ""
        parsed_json = extract_and_parse_json(response_text)

        if parsed_json and "days" in parsed_json and isinstance(parsed_json["days"], list) and len(parsed_json["days"]) >= 5:
            # Ensure safety note is present
            if not parsed_json.get("safety_note"):
                parsed_json["safety_note"] = FITNESS_SAFETY_DISCLAIMER
            return parsed_json

        logger.warning("Gemini response lacked complete 7-day structure. Using safe fallback.")
        return create_fallback_plan(
            goal=goal,
            intensity=intensity,
            note=f"Notice: Plan generated with standard balanced templates. {FITNESS_SAFETY_DISCLAIMER}"
        )

    except Exception as e:
        logger.error(f"Error calling Gemini API for workout generation: {type(e).__name__} - {e}")
        # Return friendly fallback plan rather than crashing the web application
        return create_fallback_plan(
            goal=goal,
            intensity=intensity,
            note=f"Notice: Live AI generation temporarily unavailable. Provided safe balanced routine. {FITNESS_SAFETY_DISCLAIMER}"
        )

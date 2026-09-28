"""
Feedback-Based Workout Plan Regeneration Module.
Updates and personalizes existing 7-day workout routines based on specific user feedback
while preserving original goals, safety principles, and structural integrity.
"""

import json
import logging
from typing import Dict, Any, Union
from google import genai
from google.genai import types
from app.config import settings
from app.utils import extract_and_parse_json, parse_plan_to_dict, FITNESS_SAFETY_DISCLAIMER

logger = logging.getLogger("fitbuddy.updated_plan")


def update_workout_plan(
    original_plan: Union[Dict[str, Any], str],
    feedback: str,
    user_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Sends the original plan, user details, and user feedback to Gemini to generate
    a revised, complete 7-day workout plan incorporating the requested adjustments safely.
    """
    structured_original = parse_plan_to_dict(original_plan)
    original_plan_str = json.dumps(structured_original, indent=2)

    username = user_info.get("username", "User")
    age = user_info.get("age", 25)
    weight = user_info.get("weight", 70)
    goal = user_info.get("goal", "general wellness")
    intensity = user_info.get("intensity", "medium")

    prompt = f"""
You are a senior certified fitness coach. A client has provided feedback on their current 7-day workout routine.
Your task is to revise and return a COMPLETE 7-DAY WORKOUT PLAN incorporating their feedback safely.

CLIENT PROFILE:
- Name: {username}
- Age: {age}
- Weight: {weight} kg
- Fitness Goal: {goal}
- Intensity: {intensity}

CURRENT 7-DAY PLAN:
{original_plan_str}

CLIENT FEEDBACK & REQUESTED CHANGES:
"{feedback}"

INSTRUCTIONS & SAFETY RULES:
1. Return a COMPLETE 7-day plan (Day 1 through Day 7), NOT just a summary or list of changes.
2. Incorporate the client's feedback thoughtfully (e.g. adjusting cardio, adding yoga, shifting rest days, modifying workout duration or muscle split).
3. Do NOT blindly adopt unsafe requests (e.g. extreme overtraining, zero rest, or dangerous exercises).
4. Preserve the user's primary goal ({goal}) unless the feedback explicitly requests a change.
5. Respect the intensity level ({intensity}).
6. Maintain exact JSON schema compatibility with the original plan.

OUTPUT FORMAT:
Respond with ONLY valid JSON adhering to this schema:
{{
  "days": [
    {{
      "day": "Day 1",
      "focus": "...",
      "warmup": "...",
      "exercises": [
        {{
          "name": "...",
          "sets": 3,
          "reps": "...",
          "duration": null,
          "rest": "..."
        }}
      ],
      "cooldown": "..."
    }}
  ],
  "safety_note": "{FITNESS_SAFETY_DISCLAIMER}"
}}
Ensure exactly 7 days are provided. Output ONLY raw JSON.
"""

    if not settings.has_gemini_api_key:
        logger.warning("GEMINI_API_KEY is not configured. Emulating feedback revision in demo mode.")
        revised = dict(structured_original)
        revised_days = list(revised.get("days", []))
        if revised_days:
            # Add an explicit notation of feedback into Day 1 or Day 2 for demo purposes
            revised_days[0]["focus"] = f"{revised_days[0]['focus']} (Adjusted for: {feedback[:30]})"
        revised["days"] = revised_days
        revised["safety_note"] = f"Plan updated per request: '{feedback}'. {FITNESS_SAFETY_DISCLAIMER}"
        return revised

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_WORKOUT_MODEL,
            contents=prompt.strip(),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.6,
            ),
        )

        response_text = response.text if hasattr(response, "text") and response.text else ""
        parsed = extract_and_parse_json(response_text)

        if parsed and "days" in parsed and isinstance(parsed["days"], list) and len(parsed["days"]) >= 5:
            if not parsed.get("safety_note"):
                parsed["safety_note"] = FITNESS_SAFETY_DISCLAIMER
            return parsed

        logger.warning("Gemini revision lacked complete structure. Retaining original with note.")
        structured_original["safety_note"] = f"Notice: Update requested '{feedback}', but response needed adjustments. {FITNESS_SAFETY_DISCLAIMER}"
        return structured_original

    except Exception as e:
        logger.error(f"Error calling Gemini API for plan update: {type(e).__name__} - {e}")
        structured_original["safety_note"] = f"Notice: Live AI update temporarily unavailable. {FITNESS_SAFETY_DISCLAIMER}"
        return structured_original

"""
Gemini Fast Model Nutrition & Recovery Tip Generator.
Produces concise, evidence-based nutrition or recovery advice customized to the user's goal.
Uses the configured lightweight fast model (e.g. GEMINI_TIP_MODEL).
"""

import logging
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger("fitbuddy.gemini_flash_generator")

# Quality evidence-based fallback tips categorized by goal
FALLBACK_NUTRITION_TIPS = {
    "weight loss": (
        "Focus on protein-rich whole foods, high-fiber vegetables, and plenty of water. "
        "Create a sustainable, moderate caloric deficit rather than restrictive crash diets."
    ),
    "muscle gain": (
        "Prioritize 1.6 to 2.2 grams of protein per kilogram of body weight spread throughout the day, "
        "and consume a balanced carbohydrate and protein snack within 1-2 hours post-workout."
    ),
    "strength": (
        "Fuel heavy lifting with complex carbohydrates and quality proteins. Ensure 7 to 9 hours "
        "of restful sleep each night to maximize neuromuscular recovery and tissue repair."
    ),
    "endurance": (
        "Maintain adequate glycogen stores with complex whole grains and hydrate consistently with electrolytes "
        "before, during, and after prolonged cardiovascular training sessions."
    ),
    "flexibility": (
        "Stay hydrated to maintain joint lubrication and muscle elasticity. Incorporate magnesium-rich foods "
        "like leafy greens and nuts to help prevent muscle cramping and tension."
    ),
    "general wellness": (
        "Aim for a vibrant 'rainbow plate' rich in colorful vegetables, lean proteins, and healthy fats. "
        "Drink at least 2 to 3 liters of water daily and prioritize consistent sleep schedules."
    ),
}


def generate_nutrition_tip_with_flash(goal: str) -> str:
    """
    Generates a single concise nutrition or recovery tip using Gemini Flash.
    Returns 1-2 practical, safe, evidence-based sentences.
    """
    clean_goal = goal.strip().lower()
    default_fallback = FALLBACK_NUTRITION_TIPS.get(
        clean_goal,
        "Prioritize balanced nutrition with adequate lean protein, complex carbohydrates, proper hydration, "
        "and 7-9 hours of quality sleep to support optimal recovery."
    )

    if not settings.has_gemini_api_key:
        return default_fallback

    prompt = f"""
You are an accredited sports nutritionist. Provide ONE concise, practical, evidence-based nutrition or recovery tip
for someone whose primary fitness goal is: "{goal}".

RULES:
- Length: 2 to 3 sentences maximum (under 50 words).
- Safe and sustainable only: DO NOT recommend crash dieting, extreme fasting, or untested supplements.
- Focus on practical habits: protein distribution, hydration, sleep hygiene, or balanced whole foods.
- Output ONLY the tip text itself with no quotation marks, headings, or introductory pleasantries.
"""

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_TIP_MODEL,
            contents=prompt.strip(),
            config=types.GenerateContentConfig(
                temperature=0.5,
                max_output_tokens=150,
            ),
        )
        tip_text = response.text.strip() if hasattr(response, "text") and response.text else ""
        if tip_text and len(tip_text) > 10:
            return tip_text.replace('"', '').strip()
        return default_fallback

    except Exception as e:
        logger.error(f"Error calling Gemini Flash API for nutrition tip: {type(e).__name__} - {e}")
        return default_fallback

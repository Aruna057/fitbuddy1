"""
Integration and Route Tests for FitBuddy.
Verifies Web views (HTML/Jinja2) and REST API endpoints.
All Gemini AI calls are strictly mocked. Uses an isolated SQLite database.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.config import settings

# In-memory SQLite database with StaticPool to ensure table state is shared across sessions
engine_test = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    Base.metadata.create_all(bind=engine_test)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Standard mock plan structure
MOCK_WORKOUT_PLAN = {
    "days": [
        {
            "day": "Day 1",
            "focus": "Full Body Baseline",
            "warmup": "Dynamic arm circles and hip rotations",
            "exercises": [
                {"name": "Bodyweight Squats", "sets": 3, "reps": "12", "duration": None, "rest": "60s"}
            ],
            "cooldown": "Hamstring and chest stretches"
        },
        {
            "day": "Day 2",
            "focus": "Cardio & Core",
            "warmup": "Light jog in place",
            "exercises": [
                {"name": "Plank Hold", "sets": 3, "reps": None, "duration": "30s", "rest": "45s"}
            ],
            "cooldown": "Child's pose"
        },
        {
            "day": "Day 3",
            "focus": "Rest & Mobility",
            "warmup": "Gentle neck rolls",
            "exercises": [],
            "cooldown": "Full body relaxation"
        },
        {
            "day": "Day 4",
            "focus": "Upper Body Push",
            "warmup": "Arm swings",
            "exercises": [
                {"name": "Push-ups", "sets": 3, "reps": "10", "duration": None, "rest": "60s"}
            ],
            "cooldown": "Shoulder stretch"
        },
        {
            "day": "Day 5",
            "focus": "Lower Body Leg Day",
            "warmup": "High knees",
            "exercises": [
                {"name": "Lunges", "sets": 3, "reps": "10 per leg", "duration": None, "rest": "60s"}
            ],
            "cooldown": "Quad stretch"
        },
        {
            "day": "Day 6",
            "focus": "Interval Endurance",
            "warmup": "Step-jacks",
            "exercises": [
                {"name": "Brisk Walk Intervals", "sets": 1, "reps": None, "duration": "20 mins", "rest": "Self-paced"}
            ],
            "cooldown": "Deep breathing"
        },
        {
            "day": "Day 7",
            "focus": "Full Recovery",
            "warmup": "Leisurely outdoor walk",
            "exercises": [],
            "cooldown": "Mindful meditation"
        }
    ],
    "safety_note": "FitBuddy medical disclaimer."
}

MOCK_NUTRITION_TIP = "Stay hydrated and consume adequate protein throughout the day."

MOCK_REVISED_PLAN = dict(MOCK_WORKOUT_PLAN)
MOCK_REVISED_PLAN["days"][0]["focus"] = "Full Body Baseline (Cardio Enhanced)"


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


# ==============================================================================
# WEB VIEW TESTS
# ==============================================================================

def test_homepage_loads():
    """Verify that GET / renders index.html with 200 OK and expected titles."""
    response = client.get("/")
    assert response.status_code == 200
    assert "FitBuddy" in response.text
    assert "Your AI-Powered" in response.text
    assert "Generate My Plan" in response.text


@patch("app.routes.generate_workout_gemini", return_value=MOCK_WORKOUT_PLAN)
@patch("app.routes.generate_nutrition_tip_with_flash", return_value=MOCK_NUTRITION_TIP)
def test_generate_workout_form_submission(mock_tip, mock_workout):
    """Verify that submitting the workout form creates the user and redirects to /result/{user_id}."""
    form_data = {
        "username": "Sarah Connor",
        "user_id": "sarah_c",
        "age": 29,
        "weight": 62.0,
        "goal": "strength",
        "intensity": "high"
    }

    # follow_redirects=True to test the full PRG cycle
    response = client.post("/generate-workout", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    assert "Sarah Connor" in response.text
    assert "Original Plan" in response.text
    assert "Full Body Baseline" in response.text
    assert mock_workout.called
    assert mock_tip.called


def test_generate_workout_invalid_input_renders_error():
    """Verify that invalid form submissions display validation errors on index.html."""
    bad_data = {
        "username": "A",  # too short (<2)
        "user_id": "bad user!@",  # illegal chars
        "age": 10,  # too young (<13)
        "weight": 10.0,  # too low
        "goal": "strength",
        "intensity": "extreme"  # invalid
    }
    response = client.post("/generate-workout", data=bad_data)
    assert response.status_code == 422
    assert "Validation Notice:" in response.text


@patch("app.routes.generate_workout_gemini", return_value=MOCK_WORKOUT_PLAN)
@patch("app.routes.generate_nutrition_tip_with_flash", return_value=MOCK_NUTRITION_TIP)
@patch("app.routes.update_workout_plan", return_value=MOCK_REVISED_PLAN)
def test_feedback_submission_and_version_toggle(mock_update, mock_tip, mock_workout):
    """
    Verify complete feedback cycle:
    1. Generate plan
    2. Submit feedback
    3. Verify result page shows updated plan and allows toggling to original plan.
    """
    # 1. Create plan
    client.post("/generate-workout", data={
        "username": "Bruce Wayne",
        "user_id": "bruce_w",
        "age": 35,
        "weight": 95.0,
        "goal": "muscle gain",
        "intensity": "high"
    }, follow_redirects=True)

    # 2. Check feedback page loads
    fb_page = client.get("/feedback/bruce_w")
    assert fb_page.status_code == 200
    assert "Adapt Your 7-Day Plan" in fb_page.text

    # 3. Submit feedback
    fb_res = client.post("/submit-feedback", data={
        "user_id": "bruce_w",
        "feedback": "Please add more cardiovascular intervals and stretching."
    }, follow_redirects=True)

    assert fb_res.status_code == 200
    assert "Your workout plan has been updated based on your feedback" in fb_res.text
    assert "Cardio Enhanced" in fb_res.text

    # 4. Check toggle to original plan
    orig_view = client.get("/result/bruce_w?view=original")
    assert orig_view.status_code == 200
    assert "Original Plan" in orig_view.text


def test_result_for_nonexistent_user_returns_404():
    """Verify that requesting a plan for a nonexistent user returns 404."""
    response = client.get("/result/ghost_user")
    assert response.status_code == 404
    assert "404" in response.text


# ==============================================================================
# ADMIN AUTHENTICATION TESTS
# ==============================================================================

def test_admin_dashboard_requires_login():
    """Verify that unauthenticated access to /view-all-users redirects to /admin/login."""
    response = client.get("/view-all-users", follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/login" in response.headers["Location"]


def test_admin_login_success_and_logout():
    """Verify that submitting valid credentials sets session and grants dashboard access."""
    # Attempt login with correct credentials
    login_res = client.post(
        "/admin/login",
        data={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
        follow_redirects=True
    )
    assert login_res.status_code == 200
    assert "Athletes" in login_res.text and "Dashboard" in login_res.text

    # Access dashboard directly with active session
    dash_res = client.get("/view-all-users")
    assert dash_res.status_code == 200
    assert "Athletes" in dash_res.text and "Dashboard" in dash_res.text

    # Log out
    logout_res = client.post("/admin/logout", follow_redirects=True)
    assert logout_res.status_code == 200
    assert "Coach" in logout_res.text and "Admin" in logout_res.text


def test_admin_login_invalid_credentials():
    """Verify that incorrect credentials redirect back with an error indicator."""
    res = client.post(
        "/admin/login",
        data={"username": "wrong_admin", "password": "wrong_password"},
        follow_redirects=False
    )
    assert res.status_code == 303
    assert "error=invalid_credentials" in res.headers["Location"]


# ==============================================================================
# REST API ENDPOINT TESTS
# ==============================================================================

@patch("app.routes.generate_workout_gemini", return_value=MOCK_WORKOUT_PLAN)
@patch("app.routes.generate_nutrition_tip_with_flash", return_value=MOCK_NUTRITION_TIP)
def test_api_generate_workout(mock_tip, mock_workout):
    """Verify POST /api/generate-workout returns valid JSON with 201 status."""
    payload = {
        "username": "Diana Prince",
        "user_id": "diana_p",
        "age": 27,
        "weight": 68.0,
        "goal": "endurance",
        "intensity": "high"
    }
    response = client.post("/api/generate-workout", json=payload)
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["user"]["user_id"] == "diana_p"
    assert "workout_plan" in json_data
    assert "nutrition_tip" in json_data


@patch("app.routes.generate_workout_gemini", return_value=MOCK_WORKOUT_PLAN)
@patch("app.routes.generate_nutrition_tip_with_flash", return_value=MOCK_NUTRITION_TIP)
@patch("app.routes.update_workout_plan", return_value=MOCK_REVISED_PLAN)
def test_api_submit_feedback(mock_update, mock_tip, mock_workout):
    """Verify POST /api/submit-feedback updates plan and returns 200 status."""
    # First generate
    client.post("/api/generate-workout", json={
        "username": "Barry Allen",
        "user_id": "barry_a",
        "age": 24,
        "weight": 70.0,
        "goal": "endurance",
        "intensity": "high"
    })

    # Submit feedback via API
    fb_res = client.post("/api/submit-feedback", json={
        "user_id": "barry_a",
        "feedback": "Add more hydration reminders and track intervals."
    })
    assert fb_res.status_code == 200
    fb_json = fb_res.json()
    assert fb_json["success"] is True
    assert fb_json["user_id"] == "barry_a"
    assert "updated_plan" in fb_json


@patch("app.routes.generate_workout_gemini", return_value=MOCK_WORKOUT_PLAN)
@patch("app.routes.generate_nutrition_tip_with_flash", return_value=MOCK_NUTRITION_TIP)
def test_api_get_users_and_detail(mock_tip, mock_workout):
    """Verify GET /api/users and GET /api/users/{user_id} return valid JSON."""
    client.post("/api/generate-workout", json={
        "username": "Arthur Curry",
        "user_id": "arthur_c",
        "age": 32,
        "weight": 92.0,
        "goal": "strength",
        "intensity": "medium"
    })

    # Test list endpoint
    list_res = client.get("/api/users")
    assert list_res.status_code == 200
    list_json = list_res.json()
    assert list_json["success"] is True
    assert any(u["user_id"] == "arthur_c" for u in list_json["users"])

    # Test detail endpoint
    detail_res = client.get("/api/users/arthur_c")
    assert detail_res.status_code == 200
    detail_json = detail_res.json()
    assert detail_json["success"] is True
    assert detail_json["user"]["username"] == "Arthur Curry"
    assert detail_json["workout_plan"] is not None

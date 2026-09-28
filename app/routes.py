"""
Application Routes and Endpoints for FitBuddy.
Handles HTML views (Jinja2) and REST API endpoints.
Maintains clean separation between presentation, database access, and AI services.
"""

import json
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.config import settings
from app.database import (
    get_db,
    create_user,
    get_user_by_user_id,
    get_all_users,
    delete_user,
    create_workout_plan,
    get_workout_plan,
    update_workout_plan_record,
)
from app.schemas import (
    UserInput,
    FeedbackRequest,
    GenerateWorkoutApiResponse,
    FeedbackApiResponse,
    UsersListApiResponse,
    UserDetailApiResponse,
)
from app.gemini_generator import generate_workout_gemini
from app.gemini_flash_generator import generate_nutrition_tip_with_flash
from app.updated_plan import update_workout_plan
from app.utils import parse_plan_to_dict, FITNESS_SAFETY_DISCLAIMER

logger = logging.getLogger("fitbuddy.routes")

# Configure templates directory
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


# ==============================================================================
# AUTHENTICATION HELPERS
# ==============================================================================

def is_admin_logged_in(request: Request) -> bool:
    """Check if admin session flag is set."""
    return request.session.get("is_admin") is True


# ==============================================================================
# HTML TEMPLATE ROUTES
# ==============================================================================

@router.get("/", response_class=HTMLResponse, tags=["Web Views"])
async def index_view(request: Request):
    """Renders the landing page with the fitness profile questionnaire."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "disclaimer": FITNESS_SAFETY_DISCLAIMER,
            "has_api_key": settings.has_gemini_api_key
        }
    )


@router.post("/generate-workout", response_class=HTMLResponse, tags=["Web Views"])
async def generate_workout_view(
    request: Request,
    username: str = Form(...),
    user_id: str = Form(...),
    age: int = Form(...),
    weight: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handles HTML form submission to validate input, generate workout plan and tip,
    save them to the database, and display results.
    """
    form_data = {
        "username": username,
        "user_id": user_id,
        "age": age,
        "weight": weight,
        "goal": goal,
        "intensity": intensity,
    }

    # Validate inputs with Pydantic
    try:
        user_input = UserInput(
            username=username,
            user_id=user_id,
            age=age,
            weight=weight,
            goal=goal,
            intensity=intensity
        )
    except Exception as validation_err:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "error": str(validation_err),
                "form_data": form_data,
                "disclaimer": FITNESS_SAFETY_DISCLAIMER,
                "has_api_key": settings.has_gemini_api_key
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    try:
        # Create or update user profile
        user = create_user(
            db=db,
            username=user_input.username,
            user_id=user_input.user_id,
            age=user_input.age,
            weight=user_input.weight,
            goal=user_input.goal,
            intensity=user_input.intensity
        )

        # Generate structured 7-day workout plan using Gemini
        workout_plan_dict = generate_workout_gemini(
            age=user.age,
            weight=user.weight,
            goal=user.goal,
            intensity=user.intensity
        )

        # Generate concise nutrition/recovery tip using Gemini Flash
        nutrition_tip = generate_nutrition_tip_with_flash(goal=user.goal)

        # Store in database (always preserves original_plan)
        create_workout_plan(
            db=db,
            user_id=user.user_id,
            original_plan=json.dumps(workout_plan_dict),
            nutrition_tip=nutrition_tip
        )

        # Redirect to results page (PRG pattern)
        return RedirectResponse(
            url=f"/result/{user.user_id}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        logger.exception("Error generating workout plan in HTML view")
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "title": "Generation Failed",
                "message": f"An error occurred while generating your plan: {str(e)}",
                "return_url": "/"
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/result/{user_id}", response_class=HTMLResponse, tags=["Web Views"])
async def result_view(
    request: Request,
    user_id: str,
    view: Optional[str] = None,
    updated: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Displays the user's workout plan.
    Supports toggling between original and updated plans while preserving both.
    """
    clean_uid = user_id.strip().lower()
    user = get_user_by_user_id(db, clean_uid)
    plan_record = get_workout_plan(db, clean_uid)

    if not user or not plan_record:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "message": f"Workout plan for user ID '{user_id}' was not found."
            },
            status_code=status.HTTP_404_NOT_FOUND
        )

    original_plan_dict = parse_plan_to_dict(plan_record.original_plan)
    updated_plan_dict = parse_plan_to_dict(plan_record.updated_plan) if plan_record.updated_plan else None

    # Determine which plan to display as active
    has_updated = updated_plan_dict is not None
    if view == "original" or not has_updated:
        active_plan = original_plan_dict
        active_mode = "original"
    else:
        active_plan = updated_plan_dict
        active_mode = "updated"

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "user": user,
            "plan_record": plan_record,
            "active_plan": active_plan,
            "active_mode": active_mode,
            "has_updated": has_updated,
            "nutrition_tip": plan_record.nutrition_tip,
            "feedback": plan_record.feedback,
            "just_updated": updated == "true" or updated == "1",
            "disclaimer": FITNESS_SAFETY_DISCLAIMER
        }
    )


@router.get("/feedback/{user_id}", response_class=HTMLResponse, tags=["Web Views"])
async def feedback_view(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """Renders the feedback page allowing users to request adjustments."""
    clean_uid = user_id.strip().lower()
    user = get_user_by_user_id(db, clean_uid)
    plan_record = get_workout_plan(db, clean_uid)

    if not user or not plan_record:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"message": f"User ID '{user_id}' not found."},
            status_code=status.HTTP_404_NOT_FOUND
        )

    return templates.TemplateResponse(
        request=request,
        name="feedback.html",
        context={
            "user": user,
            "existing_feedback": plan_record.feedback or "",
            "disclaimer": FITNESS_SAFETY_DISCLAIMER
        }
    )


@router.post("/submit-feedback", response_class=HTMLResponse, tags=["Web Views"])
async def submit_feedback_view(
    request: Request,
    user_id: str = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Submits user feedback, regenerates the plan using Gemini while preserving the
    original plan, and updates the database record.
    """
    try:
        feedback_req = FeedbackRequest(user_id=user_id, feedback=feedback)
    except Exception as validation_err:
        user = get_user_by_user_id(db, user_id.strip().lower())
        return templates.TemplateResponse(
            request=request,
            name="feedback.html",
            context={
                "user": user,
                "error": str(validation_err),
                "existing_feedback": feedback,
                "disclaimer": FITNESS_SAFETY_DISCLAIMER
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    user = get_user_by_user_id(db, feedback_req.user_id)
    plan_record = get_workout_plan(db, feedback_req.user_id)

    if not user or not plan_record:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"message": f"User '{feedback_req.user_id}' not found."},
            status_code=status.HTTP_404_NOT_FOUND
        )

    try:
        # Retrieve original plan to serve as base
        original_dict = parse_plan_to_dict(plan_record.original_plan)

        user_info = {
            "username": user.username,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity
        }

        # Generate revised plan based on feedback
        revised_plan_dict = update_workout_plan(
            original_plan=original_dict,
            feedback=feedback_req.feedback,
            user_info=user_info
        )

        # Store in updated_plan (original_plan remains untouched!)
        update_workout_plan_record(
            db=db,
            user_id=user.user_id,
            updated_plan=json.dumps(revised_plan_dict),
            feedback=feedback_req.feedback
        )

        return RedirectResponse(
            url=f"/result/{user.user_id}?updated=true",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        logger.exception("Error processing feedback update")
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "title": "Update Failed",
                "message": f"Failed to regenerate plan from feedback: {str(e)}",
                "return_url": f"/result/{user.user_id}"
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==============================================================================
# ADMIN AUTHENTICATION & DASHBOARD
# ==============================================================================

@router.get("/admin/login", response_class=HTMLResponse, tags=["Admin"])
async def admin_login_page(request: Request, error: Optional[str] = None):
    """Renders admin login form."""
    if is_admin_logged_in(request):
        return RedirectResponse(url="/view-all-users", status_code=status.HTTP_303_SEE_OTHER)

    error_message = None
    if error == "invalid_credentials":
        error_message = "Invalid administrator username or password."
    elif error == "auth_required":
        error_message = "Please log in to access the coach / admin dashboard."

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error_message": error_message
        }
    )


@router.post("/admin/login", response_class=HTMLResponse, tags=["Admin"])
async def admin_login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Validates admin credentials and sets session."""
    clean_user = username.strip()
    clean_pass = password.strip()

    if clean_user == settings.ADMIN_USERNAME and clean_pass == settings.ADMIN_PASSWORD:
        request.session["is_admin"] = True
        return RedirectResponse(url="/view-all-users", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url="/admin/login?error=invalid_credentials", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/logout", response_class=HTMLResponse, tags=["Admin"])
async def admin_logout_action(request: Request):
    """Logs out admin and clears session."""
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/view-all-users", response_class=HTMLResponse, tags=["Admin"])
async def view_all_users_view(request: Request, db: Session = Depends(get_db)):
    """Admin dashboard displaying all registered users and their plan statuses."""
    if not is_admin_logged_in(request):
        return RedirectResponse(url="/admin/login?error=auth_required", status_code=status.HTTP_303_SEE_OTHER)

    users = get_all_users(db)
    user_rows = []
    for u in users:
        plan = get_workout_plan(db, u.user_id)
        user_rows.append({
            "user": u,
            "has_original": plan is not None and bool(plan.original_plan),
            "has_updated": plan is not None and bool(plan.updated_plan),
            "created_date": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "N/A"
        })

    return templates.TemplateResponse(
        request=request,
        name="all_users.html",
        context={
            "user_rows": user_rows,
            "total_users": len(users),
            "admin_user": settings.ADMIN_USERNAME
        }
    )


@router.get("/user/{user_id}", response_class=HTMLResponse, tags=["Admin"])
async def user_detail_view(request: Request, user_id: str, db: Session = Depends(get_db)):
    """Admin view for detailed user information, comparison of original vs updated plans."""
    if not is_admin_logged_in(request):
        return RedirectResponse(url="/admin/login?error=auth_required", status_code=status.HTTP_303_SEE_OTHER)

    clean_uid = user_id.strip().lower()
    user = get_user_by_user_id(db, clean_uid)
    plan_record = get_workout_plan(db, clean_uid)

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"message": f"User '{user_id}' not found."},
            status_code=status.HTTP_404_NOT_FOUND
        )

    original_dict = parse_plan_to_dict(plan_record.original_plan) if plan_record else None
    updated_dict = parse_plan_to_dict(plan_record.updated_plan) if plan_record and plan_record.updated_plan else None

    return templates.TemplateResponse(
        request=request,
        name="user_detail.html",
        context={
            "user": user,
            "plan_record": plan_record,
            "original_plan": original_dict,
            "updated_plan": updated_dict,
        }
    )


@router.post("/delete-user/{user_id}", response_class=HTMLResponse, tags=["Admin"])
async def delete_user_view(request: Request, user_id: str, db: Session = Depends(get_db)):
    """Deletes a user and their associated workout plans safely."""
    if not is_admin_logged_in(request):
        return RedirectResponse(url="/admin/login?error=auth_required", status_code=status.HTTP_303_SEE_OTHER)

    clean_uid = user_id.strip().lower()
    delete_user(db, clean_uid)
    return RedirectResponse(url="/view-all-users?deleted=1", status_code=status.HTTP_303_SEE_OTHER)


# ==============================================================================
# REST API ENDPOINTS
# ==============================================================================

@router.post(
    "/api/generate-workout",
    response_model=GenerateWorkoutApiResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["REST API"]
)
async def api_generate_workout(user_input: UserInput, db: Session = Depends(get_db)):
    """
    REST API to generate a personalized 7-day workout plan and nutrition tip.
    Creates or updates the user and registers their initial workout plan.
    """
    try:
        user = create_user(
            db=db,
            username=user_input.username,
            user_id=user_input.user_id,
            age=user_input.age,
            weight=user_input.weight,
            goal=user_input.goal,
            intensity=user_input.intensity
        )

        workout_dict = generate_workout_gemini(
            age=user.age,
            weight=user.weight,
            goal=user.goal,
            intensity=user.intensity
        )

        nutrition_tip = generate_nutrition_tip_with_flash(goal=user.goal)

        create_workout_plan(
            db=db,
            user_id=user.user_id,
            original_plan=json.dumps(workout_dict),
            nutrition_tip=nutrition_tip
        )

        return GenerateWorkoutApiResponse(
            success=True,
            user=user.to_dict(),
            workout_plan=workout_dict,
            nutrition_tip=nutrition_tip,
            message="Workout plan generated successfully"
        )
    except Exception as e:
        logger.exception("API generate workout error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate workout plan: {str(e)}"
        )


@router.post(
    "/api/submit-feedback",
    response_model=FeedbackApiResponse,
    status_code=status.HTTP_200_OK,
    tags=["REST API"]
)
async def api_submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    """
    REST API to submit feedback and regenerate a revised 7-day plan.
    Preserves original_plan permanently and stores the update in updated_plan.
    """
    user = get_user_by_user_id(db, payload.user_id)
    plan_record = get_workout_plan(db, payload.user_id)

    if not user or not plan_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User or plan not found for ID: {payload.user_id}"
        )

    try:
        original_dict = parse_plan_to_dict(plan_record.original_plan)
        user_info = {
            "username": user.username,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity
        }

        revised_dict = update_workout_plan(
            original_plan=original_dict,
            feedback=payload.feedback,
            user_info=user_info
        )

        update_workout_plan_record(
            db=db,
            user_id=payload.user_id,
            updated_plan=json.dumps(revised_dict),
            feedback=payload.feedback
        )

        return FeedbackApiResponse(
            success=True,
            user_id=payload.user_id,
            updated_plan=revised_dict,
            message="Workout plan updated successfully based on feedback"
        )
    except Exception as e:
        logger.exception("API feedback submission error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workout plan: {str(e)}"
        )


@router.get(
    "/api/users",
    response_model=UsersListApiResponse,
    tags=["REST API"]
)
async def api_get_users(db: Session = Depends(get_db)):
    """REST API to retrieve all registered users."""
    users = get_all_users(db)
    return UsersListApiResponse(
        success=True,
        users=[u.to_dict() for u in users]
    )


@router.get(
    "/api/users/{user_id}",
    response_model=UserDetailApiResponse,
    tags=["REST API"]
)
async def api_get_user_detail(user_id: str, db: Session = Depends(get_db)):
    """REST API to retrieve a single user and their full workout plans."""
    clean_uid = user_id.strip().lower()
    user = get_user_by_user_id(db, clean_uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found"
        )

    plan_record = get_workout_plan(db, clean_uid)
    plan_dict = None
    if plan_record:
        plan_dict = {
            "id": plan_record.id,
            "original_plan": parse_plan_to_dict(plan_record.original_plan),
            "updated_plan": parse_plan_to_dict(plan_record.updated_plan) if plan_record.updated_plan else None,
            "nutrition_tip": plan_record.nutrition_tip,
            "feedback": plan_record.feedback,
            "created_at": plan_record.created_at.isoformat() if plan_record.created_at else None,
            "updated_at": plan_record.updated_at.isoformat() if plan_record.updated_at else None,
        }

    return UserDetailApiResponse(
        success=True,
        user=user.to_dict(),
        workout_plan=plan_dict
    )

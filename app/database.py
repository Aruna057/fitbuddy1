"""
Database Configuration and CRUD Operations for FitBuddy.
Manages SQLAlchemy engine, session lifecycle, and database queries.
"""

from typing import Optional, List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from app.models import Base, User, WorkoutPlan, get_utc_now

# Connect to SQLite. check_same_thread=False allows multi-threaded requests in FastAPI
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables in the database if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    FastAPI dependency yielding a SQLAlchemy session.
    Ensures sessions are cleanly closed after each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================================
# USER CRUD FUNCTIONS
# ==============================================================================

def create_user(
    db: Session,
    username: str,
    user_id: str,
    age: int,
    weight: float,
    goal: str,
    intensity: str
) -> User:
    """
    Create a new user or update an existing user's details if user_id exists.
    Handles duplicates gracefully.
    """
    existing_user = db.query(User).filter(User.user_id == user_id).first()
    if existing_user:
        existing_user.username = username
        existing_user.age = age
        existing_user.weight = weight
        existing_user.goal = goal
        existing_user.intensity = intensity
        db.commit()
        db.refresh(existing_user)
        return existing_user

    new_user = User(
        username=username,
        user_id=user_id,
        age=age,
        weight=weight,
        goal=goal,
        intensity=intensity,
        created_at=get_utc_now()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def get_user_by_user_id(db: Session, user_id: str) -> Optional[User]:
    """Retrieve user by their unique user_id."""
    return db.query(User).filter(User.user_id == user_id).first()


def get_user_by_id(db: Session, id: int) -> Optional[User]:
    """Retrieve user by their integer primary key id."""
    return db.query(User).filter(User.id == id).first()


def get_all_users(db: Session) -> List[User]:
    """Retrieve all registered users ordered by creation date descending."""
    return db.query(User).order_by(User.created_at.desc()).all()


def delete_user(db: Session, user_id: str) -> bool:
    """
    Delete a user by user_id.
    Associated workout plans will be deleted via cascade.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


# ==============================================================================
# WORKOUT PLAN CRUD FUNCTIONS
# ==============================================================================

def create_workout_plan(
    db: Session,
    user_id: str,
    original_plan: str,
    nutrition_tip: Optional[str] = None
) -> WorkoutPlan:
    """
    Create or reset workout plan for a user.
    Preserves original_plan. Initially updated_plan and feedback are None.
    """
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).first()
    if plan:
        plan.original_plan = original_plan
        plan.updated_plan = None
        plan.feedback = None
        plan.nutrition_tip = nutrition_tip
        plan.updated_at = get_utc_now()
        db.commit()
        db.refresh(plan)
        return plan

    new_plan = WorkoutPlan(
        user_id=user_id,
        original_plan=original_plan,
        updated_plan=None,
        nutrition_tip=nutrition_tip,
        feedback=None,
        created_at=get_utc_now(),
        updated_at=get_utc_now()
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    return new_plan


def get_workout_plan(db: Session, user_id: str) -> Optional[WorkoutPlan]:
    """Retrieve the workout plan record for a given user_id."""
    return db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).first()


def update_workout_plan_record(
    db: Session,
    user_id: str,
    updated_plan: str,
    feedback: str
) -> Optional[WorkoutPlan]:
    """
    Save the revised plan in updated_plan and record the user feedback.
    Guarantees that original_plan is permanently preserved.
    """
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).first()
    if not plan:
        return None

    plan.updated_plan = updated_plan
    plan.feedback = feedback
    plan.updated_at = get_utc_now()
    db.commit()
    db.refresh(plan)
    return plan


def get_original_plan(db: Session, user_id: str) -> Optional[str]:
    """Retrieve only the original plan string for a user."""
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).first()
    return plan.original_plan if plan else None


def get_updated_plan(db: Session, user_id: str) -> Optional[str]:
    """Retrieve only the updated plan string for a user."""
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).first()
    return plan.updated_plan if plan else None

"""
Unit Tests for Database Operations and SQLAlchemy Models.
Tests user creation, duplicate handling, plan persistence, cascading deletes, and retrieval.
Uses an in-memory SQLite database for complete test isolation.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, WorkoutPlan
from app.database import (
    create_user,
    get_user_by_user_id,
    get_user_by_id,
    get_all_users,
    delete_user,
    create_workout_plan,
    get_workout_plan,
    update_workout_plan_record,
    get_original_plan,
    get_updated_plan,
)


@pytest.fixture(name="db_session")
def fixture_db_session():
    """Provides an isolated in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_user_creation_and_retrieval(db_session):
    """Verify that users can be created and retrieved by user_id and primary key."""
    user = create_user(
        db=db_session,
        username="Marcus Aurelius",
        user_id="marcus_01",
        age=45,
        weight=82.0,
        goal="strength",
        intensity="high"
    )
    assert user.id is not None
    assert user.username == "Marcus Aurelius"
    assert user.user_id == "marcus_01"

    # Retrieve by user_id
    retrieved = get_user_by_user_id(db_session, "marcus_01")
    assert retrieved is not None
    assert retrieved.user_id == "marcus_01"
    assert retrieved.age == 45

    # Retrieve by integer primary key
    retrieved_by_id = get_user_by_id(db_session, user.id)
    assert retrieved_by_id is not None
    assert retrieved_by_id.user_id == "marcus_01"


def test_duplicate_user_handling(db_session):
    """Verify that submitting an existing user_id updates the user profile gracefully without duplicating."""
    user1 = create_user(
        db=db_session,
        username="Initial Name",
        user_id="dup_user",
        age=25,
        weight=70.0,
        goal="weight loss",
        intensity="low"
    )
    initial_id = user1.id

    # Update with the same user_id
    user2 = create_user(
        db=db_session,
        username="Updated Name",
        user_id="dup_user",
        age=26,
        weight=68.0,
        goal="muscle gain",
        intensity="medium"
    )

    assert user2.id == initial_id
    assert user2.username == "Updated Name"
    assert user2.age == 26
    assert user2.weight == 68.0

    # Ensure only 1 record exists in table
    all_users = get_all_users(db_session)
    assert len(all_users) == 1


def test_workout_plan_storage_and_permanence(db_session):
    """
    Verify that:
    1. original_plan is permanently stored.
    2. updated_plan is initially None.
    3. Updating plan records the revised plan and feedback without altering original_plan.
    """
    create_user(
        db=db_session,
        username="Test Athlete",
        user_id="athlete_1",
        age=30,
        weight=75.0,
        goal="general wellness",
        intensity="medium"
    )

    original_json = '{"days": [{"day": "Day 1", "focus": "Cardio"}]}'
    plan = create_workout_plan(
        db=db_session,
        user_id="athlete_1",
        original_plan=original_json,
        nutrition_tip="Drink water."
    )
    assert plan.id is not None
    assert plan.original_plan == original_json
    assert plan.updated_plan is None
    assert plan.feedback is None
    assert plan.nutrition_tip == "Drink water."

    # Update with user feedback
    revised_json = '{"days": [{"day": "Day 1", "focus": "Strength"}]}'
    user_feedback = "Swap cardio with strength."
    updated_record = update_workout_plan_record(
        db=db_session,
        user_id="athlete_1",
        updated_plan=revised_json,
        feedback=user_feedback
    )

    assert updated_record is not None
    # Crucial test: original_plan MUST NOT be overwritten
    assert updated_record.original_plan == original_json
    assert updated_record.updated_plan == revised_json
    assert updated_record.feedback == user_feedback

    # Test helper retrieval functions
    assert get_original_plan(db_session, "athlete_1") == original_json
    assert get_updated_plan(db_session, "athlete_1") == revised_json


def test_user_deletion_cascades_plans(db_session):
    """Verify that deleting a user removes the user and cascades to delete their workout plans."""
    create_user(
        db=db_session,
        username="To Be Deleted",
        user_id="del_user",
        age=22,
        weight=60.0,
        goal="flexibility",
        intensity="low"
    )
    create_workout_plan(
        db=db_session,
        user_id="del_user",
        original_plan='{"days": []}',
        nutrition_tip="Eat fruits."
    )

    # Verify existence
    assert get_user_by_user_id(db_session, "del_user") is not None
    assert get_workout_plan(db_session, "del_user") is not None

    # Delete
    deleted = delete_user(db_session, "del_user")
    assert deleted is True

    # Verify both user and plan are gone
    assert get_user_by_user_id(db_session, "del_user") is None
    assert get_workout_plan(db_session, "del_user") is None

    # Attempting to delete non-existent user returns False
    assert delete_user(db_session, "non_existent") is False

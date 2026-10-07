import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.activity import Activity
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goals import GoalCreate, GoalResponse, GoalUpdate


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/goals", tags=["goals"])


def _commit_goal(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        logger.error("goal_write_conflict", extra={"error_type": type(error).__name__})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Goal could not be saved because of a data conflict",
        ) from error
    except SQLAlchemyError as error:
        session.rollback()
        logger.error("goal_database_error", extra={"error_type": type(error).__name__})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Goal could not be saved",
        ) from error


def _goal_progress(goal: Goal, current_co2e: Decimal) -> tuple[Decimal, Decimal, bool]:
    if current_co2e <= goal.target_co2e:
        is_completed = True
    else:
        is_completed = False

    span = goal.baseline_co2e - goal.target_co2e
    if span > 0:
        reduction_remaining = goal.baseline_co2e - goal.target_co2e
        if reduction_remaining > 0:
            progress = ((goal.baseline_co2e - current_co2e) / reduction_remaining) * Decimal("100")
            progress = max(Decimal("0"), min(progress, Decimal("100")))
        else:
            progress = Decimal("100")
    else:
        progress = Decimal("100") if current_co2e <= goal.target_co2e else Decimal("0")

    remaining_co2e = max(goal.target_co2e - current_co2e, Decimal("0"))
    return progress.quantize(Decimal("0.01")), remaining_co2e, is_completed


def _serialize_goal(session: Session, goal: Goal, current_user_id: UUID) -> GoalResponse:
    current_co2e = session.scalar(
        select(func.coalesce(func.sum(Activity.calculated_co2e), Decimal("0"))).where(
            Activity.user_id == current_user_id,
            Activity.activity_date >= goal.start_date,
            Activity.activity_date <= goal.end_date,
        )
    )
    current_co2e = Decimal(current_co2e or Decimal("0"))
    progress_percent, remaining_co2e, is_completed = _goal_progress(goal, current_co2e)
    return GoalResponse(
        id=goal.id,
        name=goal.name,
        target_type=goal.target_type,
        baseline_co2e=goal.baseline_co2e,
        target_co2e=goal.target_co2e,
        start_date=goal.start_date,
        end_date=goal.end_date,
        is_completed=is_completed,
        current_co2e=current_co2e,
        progress_percent=progress_percent,
        remaining_co2e=remaining_co2e,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


def _get_owned_goal(session: Session, goal_id: UUID, user_id: UUID) -> Goal:
    goal = session.get(Goal, goal_id)
    if goal is None or goal.user_id != user_id:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.get("", response_model=list[GoalResponse], summary="List goals")
def list_goals(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GoalResponse]:
    goals = session.scalars(
        select(Goal).where(Goal.user_id == current_user.id).order_by(Goal.start_date.desc())
    ).all()
    return [_serialize_goal(session, goal, current_user.id) for goal in goals]


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED, summary="Create a goal")
def create_goal(
    payload: GoalCreate,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    goal = Goal(
        user_id=current_user.id,
        name=payload.name,
        target_type=payload.target_type,
        baseline_co2e=payload.baseline_co2e,
        target_co2e=payload.target_co2e,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    session.add(goal)
    session.flush()
    result = _serialize_goal(session, goal, current_user.id)
    _commit_goal(session)
    return result


@router.get("/{goal_id}", response_model=GoalResponse, summary="Get a goal")
def get_goal(
    goal_id: UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    goal = _get_owned_goal(session, goal_id, current_user.id)
    return _serialize_goal(session, goal, current_user.id)


@router.put("/{goal_id}", response_model=GoalResponse, summary="Update a goal")
def update_goal(
    goal_id: UUID,
    payload: GoalUpdate,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    goal = _get_owned_goal(session, goal_id, current_user.id)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, field_name, value)
    session.flush()
    result = _serialize_goal(session, goal, current_user.id)
    _commit_goal(session)
    return result


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a goal")
def delete_goal(
    goal_id: UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    goal = _get_owned_goal(session, goal_id, current_user.id)
    session.delete(goal)
    _commit_goal(session)

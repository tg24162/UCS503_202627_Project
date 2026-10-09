import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from dependencies import CurrentUser, DbSession
from models import Category, RecurringPayment
from schemas import RecurringPaymentCreate, RecurringPaymentOut, RecurringPaymentUpdate

router = APIRouter(prefix="/recurring-payments", tags=["recurring-payments"])


def _get_owned_recurring_payment(
    db, user_id: uuid.UUID, payment_id: uuid.UUID
) -> RecurringPayment:
    payment = db.scalar(
        select(RecurringPayment)
        .options(selectinload(RecurringPayment.category))
        .where(RecurringPayment.id == payment_id, RecurringPayment.user_id == user_id)
    )
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recurring payment not found"
        )
    return payment


def _validate_category(db, category_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found"
        )


@router.post("", response_model=RecurringPaymentOut, status_code=status.HTTP_201_CREATED)
def create_recurring_payment(
    payload: RecurringPaymentCreate, db: DbSession, current_user: CurrentUser
):
    _validate_category(db, payload.category_id)

    payment = RecurringPayment(
        user_id=current_user.id,
        name=payload.name,
        amount=payload.amount,
        frequency=payload.frequency,
        next_due_date=payload.next_due_date,
        category_id=payload.category_id,
        is_active=True,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("", response_model=list[RecurringPaymentOut])
def list_recurring_payments(
    db: DbSession,
    current_user: CurrentUser,
    include_inactive: bool = False,
    category_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(RecurringPayment).where(RecurringPayment.user_id == current_user.id)
    if not include_inactive:
        query = query.where(RecurringPayment.is_active.is_(True))
    if category_id is not None:
        query = query.where(RecurringPayment.category_id == category_id)

    return db.scalars(
        query.options(selectinload(RecurringPayment.category))
        .order_by(RecurringPayment.next_due_date.asc(), RecurringPayment.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()


@router.put("/{payment_id}", response_model=RecurringPaymentOut)
def update_recurring_payment(
    payment_id: uuid.UUID, payload: RecurringPaymentUpdate, db: DbSession, current_user: CurrentUser
):
    payment = _get_owned_recurring_payment(db, current_user.id, payment_id)

    updates = payload.model_dump(exclude_unset=True)
    if "category_id" in updates:
        _validate_category(db, updates["category_id"])

    for field, value in updates.items():
        setattr(payment, field, value)

    db.commit()
    db.refresh(payment)
    return payment


@router.delete("/{payment_id}", response_model=RecurringPaymentOut)
def cancel_recurring_payment(
    payment_id: uuid.UUID, db: DbSession, current_user: CurrentUser
):
    payment = _get_owned_recurring_payment(db, current_user.id, payment_id)
    payment.is_active = False
    db.commit()
    db.refresh(payment)
    return payment
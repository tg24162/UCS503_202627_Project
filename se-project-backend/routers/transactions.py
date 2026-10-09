import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from dependencies import CurrentUser, DbSession
from models import Category, Transaction, TransactionSource
from schemas import (
    TransactionCreate,
    TransactionListOut,
    TransactionOut,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _get_owned_transaction(db, user_id: uuid.UUID, transaction_id: uuid.UUID) -> Transaction:
    transaction = db.scalar(
        select(Transaction)
        .options(selectinload(Transaction.category))
        .where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    return transaction


def _validate_category(db, category_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found"
        )


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, db: DbSession, current_user: CurrentUser):
    _validate_category(db, payload.category_id)

    transaction = Transaction(
        user_id=current_user.id,
        amount=payload.amount,
        currency=payload.currency,
        transaction_date=payload.transaction_date,
        item_name=payload.item_name,
        category_id=payload.category_id,
        payment_method=payload.payment_method,
        place=payload.place,
        source=TransactionSource.manual,
        ocr_confidence=None,
        needs_review=False,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("", response_model=TransactionListOut)
def list_transactions(
    db: DbSession,
    current_user: CurrentUser,
    category_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    base_query = select(Transaction).where(Transaction.user_id == current_user.id)
    total_query = select(func.count()).select_from(Transaction).where(
        Transaction.user_id == current_user.id
    )

    if category_id is not None:
        base_query = base_query.where(Transaction.category_id == category_id)
        total_query = total_query.where(Transaction.category_id == category_id)
    if date_from is not None:
        base_query = base_query.where(Transaction.transaction_date >= date_from)
        total_query = total_query.where(Transaction.transaction_date >= date_from)
    if date_to is not None:
        base_query = base_query.where(Transaction.transaction_date <= date_to)
        total_query = total_query.where(Transaction.transaction_date <= date_to)

    total = db.scalar(total_query) or 0
    items = db.scalars(
        base_query.options(selectinload(Transaction.category))
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return TransactionListOut(total=total, items=items)


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    return _get_owned_transaction(db, current_user.id, transaction_id)


@router.put("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: uuid.UUID, payload: TransactionUpdate, db: DbSession, current_user: CurrentUser
):
    transaction = _get_owned_transaction(db, current_user.id, transaction_id)

    updates = payload.model_dump(exclude_unset=True)
    if "category_id" in updates:
        _validate_category(db, updates["category_id"])

    for field, value in updates.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    transaction = _get_owned_transaction(db, current_user.id, transaction_id)
    db.delete(transaction)
    db.commit()
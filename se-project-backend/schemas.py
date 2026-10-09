import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from models import (
    PaymentMethod,
    RecurringFrequency,
    TransactionSource,
)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    display_name: str | None = None
    user_category: str | None = None
    priorities: list[str] | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str | None
    user_category: str | None
    priorities: list[str] | None
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_default: bool


class TransactionCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="INR", max_length=3)
    transaction_date: datetime
    item_name: str = Field(min_length=1, max_length=255)
    category_id: int | None = None
    payment_method: PaymentMethod
    place: str | None = Field(default=None, max_length=255)


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, max_length=3)
    transaction_date: datetime | None = None
    item_name: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: int | None = None
    payment_method: PaymentMethod | None = None
    place: str | None = Field(default=None, max_length=255)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    amount: Decimal
    currency: str
    transaction_date: datetime
    item_name: str
    category_id: int | None
    category: CategoryOut | None = None
    payment_method: PaymentMethod
    place: str | None
    source: TransactionSource
    ocr_confidence: float | None
    needs_review: bool
    raw_ocr_text: str | None
    created_at: datetime
    updated_at: datetime


class TransactionListOut(BaseModel):
    total: int
    items: list[TransactionOut]


class RecurringPaymentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0)
    frequency: RecurringFrequency
    next_due_date: date
    category_id: int | None = None


class RecurringPaymentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    amount: Decimal | None = Field(default=None, gt=0)
    frequency: RecurringFrequency | None = None
    next_due_date: date | None = None
    category_id: int | None = None
    is_active: bool | None = None


class RecurringPaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    amount: Decimal
    frequency: RecurringFrequency
    next_due_date: date
    category_id: int | None
    category: CategoryOut | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
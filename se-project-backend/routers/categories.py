from fastapi import APIRouter
from sqlalchemy import select

from dependencies import CurrentUser, DbSession
from models import Category
from schemas import CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: DbSession, current_user: CurrentUser):
    return db.scalars(select(Category).order_by(Category.id.asc())).all()
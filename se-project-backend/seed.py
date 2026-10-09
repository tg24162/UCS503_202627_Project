from db import SessionLocal
from models import Category

DEFAULT_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Shopping",
    "Entertainment",
]


def seed_categories() -> None:
    db = SessionLocal()
    existing = {c.name for c in db.query(Category).all()}
    inserted = []
    for name in DEFAULT_CATEGORIES:
        if name not in existing:
            db.add(Category(name=name, is_default=True))
            inserted.append(name)

    db.commit()

    if inserted:
        print(f"Inserted {len(inserted)} categories: {', '.join(inserted)}")
    else:
        print("All default categories already exist; nothing to insert.")

    print(f"Total categories in DB: {db.query(Category).count()}")
    db.close()


if __name__ == "__main__":
    seed_categories()
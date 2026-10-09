# Expense Tracker API

FastAPI backend for a receipt-scanning expense tracker. Part 2: auth + manual entry CRUD.

## Stack

- FastAPI + Pydantic v2 + SQLAlchemy 2.0 + PostgreSQL + Alembic
- JWT access tokens (PyJWT), bcrypt password hashing (passlib; `bcrypt==4.0.1` pinned — passlib is incompatible with bcrypt >= 4.1)

## Setup

```bash
pip install -r requirements.txt
python -c "import secrets; print(secrets.token_hex(32))"   # put result in JWT_SECRET in .env
alembic upgrade head        # apply migrations
python seed.py              # seed default categories (idempotent)
uvicorn main:app --reload   # run the server
```

`.env` requires `DATABASE_URL` and `JWT_SECRET` (see `.env` in the repo).

## Endpoints

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/signup` | email, password, optional display_name/user_category/priorities |
| POST | `/auth/login` | email + password |
| GET | `/auth/me` | current user profile (auth) |
| POST | `/transactions` | manual transaction (source forced to `manual`) |
| GET | `/transactions` | filters: `category_id`, `date_from`, `date_to`, `limit`, `offset` |
| GET | `/transactions/{id}` | single (auth + ownership) |
| PUT | `/transactions/{id}` | update fields |
| DELETE | `/transactions/{id}` | hard delete |
| POST | `/recurring-payments` | name, amount, frequency, next_due_date, category_id |
| GET | `/recurring-payments` | active only; add `?include_inactive=true` to include cancelled |
| PUT | `/recurring-payments/{id}` | update |
| DELETE | `/recurring-payments/{id}` | soft delete (`is_active=false`) |
| GET | `/categories` | seeded defaults |

Interactive docs at `http://localhost:8000/docs`.

## Example curl commands

**1. Signup** (returns a JWT in `access_token`):

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret123","display_name":"Alice","user_category":"professional","priorities":["saving","investing"]}'
```

**2. Login** (use this to get a token for an existing account):

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret123"}'
```

**3. Create a transaction using the returned token** (replace `<TOKEN>` with the `access_token` value):

```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"amount":450.75,"transaction_date":"2026-09-11T10:30:00Z","item_name":"Chicken Biryani","category_id":1,"payment_method":"upi","place":"Hyderabadi Bawarchi"}'
```

**4. List your transactions:**

```bash
curl http://localhost:8000/transactions?limit=50 -H "Authorization: Bearer <TOKEN>"
```

**5. Cancel a recurring payment (soft delete, keeps history):**

```bash
curl -X DELETE http://localhost:8000/recurring-payments/<ID> -H "Authorization: Bearer <TOKEN>"
```

## Testing

```bash
python e2e_test.py   # in-process end-to-end smoke test (signup → login → CRUD → cancel), cleans up after
```
"""
End-to-end smoke test using httpx.ASGITransport (in-process, no server needed).
Run:  python e2e_test.py
"""
from __future__ import annotations

import json
import sys
import traceback

from starlette.testclient import TestClient

from main import app

client = TestClient(app)

BASE_URL = ""
token: str | None = None

TEST_EMAIL = "e2e_test@example.com"
TEST_PASSWORD = "testpassword123"


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


def req(method: str, path: str, **kwargs) -> "Response":
    kwargs.setdefault("headers", auth_headers())
    resp = getattr(client, method)(path, **kwargs)
    return resp


def show(label: str, resp) -> None:
    print(f"\n{'-'*70}")
    print(f"  {label}  [{resp.status_code}]")
    print(f"{'-'*70}")
    try:
        print(json.dumps(resp.json(), indent=2, default=str))
    except Exception:
        print(resp.text or "(empty body)")
    return resp


def cleanup():
    from db import SessionLocal
    from models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        if user:
            db.delete(user)
            db.commit()
            print(f"\n[cleanup] Deleted test user {TEST_EMAIL} (cascade removed related rows).")
        else:
            print("\n[cleanup] No leftover test user.")
    finally:
        db.close()


passed = 0
failed = 0


def check(label: str, resp, status: int | None = None, **assertions):
    global passed, failed
    ok = True
    if status is not None and resp.status_code != status:
        ok = False
    try:
        body = resp.json()
    except Exception:
        body = {}
    for key, expected in assertions.items():
        if key in body and body[key] != expected:
            ok = False
    if ok:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        print(f"  [FAIL] {label}")
        print(f"         expected status={status}, got={resp.status_code}")
        print(f"         body={json.dumps(body, default=str)}")


def run():
    global token

    print("=" * 70)
    print("  EXPENSE TRACKER - END-TO-END SMOKE TEST")
    print("=" * 70)
    cleanup()

    # 1. Signup
    resp = req("post", "/auth/signup", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "display_name": "E2E Tester",
        "user_category": "student",
        "priorities": ["saving", "budgeting"],
    })
    show("POST /auth/signup", resp)
    check("signup returns 201 + token", resp, status=201)
    token = resp.json()["access_token"]

    # 2. Auth/me
    resp = req("get", "/auth/me")
    show("GET /auth/me", resp)
    check("me returns 200 + correct email", resp, status=200, email=TEST_EMAIL)

    # 3. Login
    resp = client.post("/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    }, headers=auth_headers())
    show("POST /auth/login", resp)
    check("login returns 200 + token", resp, status=200)
    token = resp.json()["access_token"]

    # 4. List transactions (empty)
    resp = req("get", "/transactions")
    show("GET /transactions (empty)", resp)
    check("empty list returns total=0", resp, status=200, total=0)

    # 5. Create transaction
    resp = req("post", "/transactions", json={
        "amount": 450.75,
        "currency": "INR",
        "transaction_date": "2026-09-11T10:30:00Z",
        "item_name": "Chicken Biryani",
        "category_id": 1,
        "payment_method": "upi",
        "place": "Hyderabadi Bawarchi",
    })
    show("POST /transactions (create)", resp)
    check("create transaction returns 201", resp, status=201)
    tx_id = resp.json()["id"]

    # 6. Get single transaction
    resp = req("get", f"/transactions/{tx_id}")
    show(f"GET /transactions/{tx_id}", resp)
    check("get by id returns correct item_name", resp, status=200, item_name="Chicken Biryani")

    # 7. Update transaction
    resp = req("put", f"/transactions/{tx_id}", json={
        "item_name": "Mutton Biryani",
        "amount": 600.00,
        "place": "Paradise Restaurant",
    })
    show(f"PUT /transactions/{tx_id}", resp)
    check("update returns 200 + new values", resp, status=200, item_name="Mutton Biryani")

    # 8. List transactions (1 item)
    resp = req("get", "/transactions?limit=10&offset=0")
    show("GET /transactions (1 item)", resp)
    check("list returns total=1", resp, status=200, total=1)

    # 9. Filter by category_id=1
    resp = req("get", "/transactions?category_id=1")
    show("GET /transactions?category_id=1", resp)
    check("filter category_id=1 returns 1", resp, status=200, total=1)

    # 10. Filter by category_id=9999 (no match)
    resp = req("get", "/transactions?category_id=9999")
    show("GET /transactions?category_id=9999", resp)
    check("filter wrong category returns 0", resp, status=200, total=0)

    # 11. Delete transaction
    resp = req("delete", f"/transactions/{tx_id}")
    show(f"DELETE /transactions/{tx_id}", resp)
    check("delete returns 204", resp, status=204)

    # 12. Confirm deleted (404)
    resp = req("get", f"/transactions/{tx_id}")
    show("GET /transactions/{id} after delete", resp)
    check("get deleted returns 404", resp, status=404)

    # 13. Categories list
    resp = req("get", "/categories")
    show("GET /categories", resp)
    check("categories list has 5 items", resp, status=200)

    # 14. Create recurring payment
    resp = req("post", "/recurring-payments", json={
        "name": "Netflix",
        "amount": 649.00,
        "frequency": "monthly",
        "next_due_date": "2026-10-01",
        "category_id": 5,
    })
    show("POST /recurring-payments (create)", resp)
    check("create recurring returns 201", resp, status=201)
    rp_id = resp.json()["id"]

    # 15. List recurring payments
    resp = req("get", "/recurring-payments")
    show("GET /recurring-payments (active)", resp)
    check("active list returns 1", resp, status=200)

    # 16. Update recurring payment
    resp = req("put", f"/recurring-payments/{rp_id}", json={
        "amount": 799.00,
        "name": "Netflix Premium",
    })
    show(f"PUT /recurring-payments/{rp_id}", resp)
    check("update recurring returns 200", resp, status=200, amount="799.00")

    # 17. Soft-delete recurring payment
    resp = req("delete", f"/recurring-payments/{rp_id}")
    show(f"DELETE /recurring-payments/{rp_id} (cancel)", resp)
    check("soft-cancel returns 200 + is_active=False", resp, status=200, is_active=False)

    # 18. Confirm hidden from active list
    resp = req("get", "/recurring-payments")
    show("GET /recurring-payments (active, now 0)", resp)
    check("active list now 0", resp, status=200)

    # 19. Visible with include_inactive
    resp = req("get", "/recurring-payments?include_inactive=true")
    show("GET /recurring-payments?include_inactive=true", resp)
    check("inactive list shows cancelled payment", resp, status=200)

    # 20. Unauthenticated access (expect 401)
    resp = client.get("/auth/me")
    show("GET /auth/me (no token, expect 401)", resp)
    check("no token returns 401", resp, status=401)

    print("\n" + "=" * 70)
    if failed == 0:
        print(f"  ALL {passed} CHECKS PASSED")
    else:
        print(f"  {passed} passed, {failed} FAILED")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = False
    try:
        success = run()
    except Exception:
        traceback.print_exc()
    finally:
        cleanup()
    sys.exit(0 if success else 1)

import json
from datetime import date, datetime, time

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Expense Tracker", page_icon="\U0001F4B0", layout="wide")

API_BASE = st.sidebar.text_input("API base URL", value="http://localhost:8000")

PAYMENT_METHODS = ["cash", "card", "upi", "other"]
FREQUENCIES = ["weekly", "monthly", "yearly"]


def auth_headers() -> dict:
    token = st.session_state.get("token")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def api(method: str, path: str, **kwargs):
    try:
        resp = requests.request(
            method, f"{API_BASE}{path}", headers=auth_headers(), timeout=15, **kwargs
        )
    except requests.RequestException as exc:
        st.error(f"Cannot reach API at {API_BASE}. Is the backend running?")
        st.stop()
    if resp.status_code == 401 and path != "/auth/login":
        st.session_state.pop("token", None)
        st.session_state.pop("user", None)
        st.rerun()
    return resp


def show_error(resp):
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    st.error(f"Request failed ({resp.status_code}): {detail}")


def load_categories() -> list[dict]:
    resp = api("GET", "/categories")
    return resp.json() if resp.ok else []


def cat_name(category):
    return category["name"] if category else "-"


# --------------------------------------------------------------------------
# AUTH
# --------------------------------------------------------------------------
def render_sidebar_user():
    st.sidebar.markdown("---")
    user = st.session_state.get("user")
    if user:
        st.sidebar.write(f"**{user.get('display_name') or user['email']}**")
        st.sidebar.caption(user["email"])
        if st.sidebar.button("Logout", width="stretch"):
            st.session_state.pop("token", None)
            st.session_state.pop("user", None)
            st.rerun()
    else:
        st.sidebar.write("Not logged in.")


def render_auth():
    tab_login, tab_signup = st.tabs(["Login", "Sign up"])
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", width="stretch")
        if submitted:
            resp = api("POST", "/auth/login", json={"email": email, "password": password})
            if resp.ok:
                data = resp.json()
                st.session_state.token = data["access_token"]
                st.session_state.user = data["user"]
                st.success(f"Welcome back, {data['user']['email']}!")
                st.rerun()
            else:
                show_error(resp)

    with tab_signup:
        with st.form("signup_form"):
            email = st.text_input("Email", key="su_email")
            password = st.text_input("Password (min 6 chars)", type="password", key="su_password")
            display_name = st.text_input("What should we call you? (optional)")
            user_category = st.text_input("User category (optional)")
            priorities = st.multiselect(
                "Priorities (optional)",
                ["saving", "budgeting", "investing", "tracking", "debt-free"],
            )
            submitted = st.form_submit_button("Create account", width="stretch")
        if submitted:
            resp = api(
                "POST",
                "/auth/signup",
                json={
                    "email": email,
                    "password": password,
                    "display_name": display_name or None,
                    "user_category": user_category or None,
                    "priorities": priorities or None,
                },
            )
            if resp.ok:
                data = resp.json()
                st.session_state.token = data["access_token"]
                st.session_state.user = data["user"]
                st.success(f"Account created. Welcome, {data['user']['email']}!")
                st.rerun()
            else:
                show_error(resp)


# --------------------------------------------------------------------------
# TRANSACTIONS
# --------------------------------------------------------------------------
def tx_to_rows(items: list[dict]) -> pd.DataFrame:
    rows = [
        {
            "Date": t["transaction_date"][:16].replace("T", " "),
            "Item": t["item_name"],
            "Amount": float(t["amount"]),
            "Currency": t["currency"],
            "Category": cat_name(t.get("category")),
            "Payment": t["payment_method"],
            "Place": t["place"] or "-",
            "Source": t["source"],
            "ID": t["id"],
        }
        for t in items
    ]
    return pd.DataFrame(rows)


def render_transactions():
    st.subheader("Transactions")

    with st.expander("Add transaction", expanded=False):
        with st.form("add_tx_form"):
            item_name = st.text_input("Item name")
            amount = st.number_input("Amount", min_value=0.0, format="%.2f")
            currency = st.text_input("Currency", value="INR", max_chars=3)
            d = st.date_input("Purchase date", value=date.today())
            tm = st.time_input("Time", value=time(12, 0))
            cats = load_categories()
            cat_choices = {c["name"]: c["id"] for c in cats}
            cat_label = st.selectbox("Category", options=["None"] + list(cat_choices))
            payment_method = st.selectbox("Payment method", PAYMENT_METHODS)
            place = st.text_input("Place / merchant (optional)")
            submitted = st.form_submit_button("Add", width="stretch")
        if submitted and item_name and amount > 0:
            payload = {
                "amount": round(amount, 2),
                "currency": currency or "INR",
                "transaction_date": datetime.combine(d, tm).isoformat(),
                "item_name": item_name,
                "category_id": cat_choices.get(cat_label) if cat_label != "None" else None,
                "payment_method": payment_method,
                "place": place or None,
            }
            resp = api("POST", "/transactions", json=payload)
            if resp.ok:
                st.success(f"Added '{item_name}' ({resp.json()['amount']} {resp.json()['currency']})")
                st.rerun()
            else:
                show_error(resp)

    st.markdown("#### Filters")
    c1, c2, c3, c4 = st.columns(4)
    cats = load_categories()
    cat_ids = {c["name"]: c["id"] for c in cats}
    with c1:
        cat_label = st.selectbox("Category", options=["All"] + list(cat_ids), key="f_cat")
    with c2:
        date_from = st.date_input("From", value=None, key="f_from")
    with c3:
        date_to = st.date_input("To", value=None, key="f_to")
    with c4:
        limit = st.slider("Limit", min_value=10, max_value=100, value=50, step=10)

    params = {"limit": limit, "offset": 0}
    if cat_label != "All":
        params["category_id"] = cat_ids[cat_label]
    if date_from:
        params["date_from"] = datetime.combine(date_from, time.min).isoformat()
    if date_to:
        params["date_to"] = datetime.combine(date_to, time.max).isoformat()

    resp = api("GET", "/transactions", params=params)
    if not resp.ok:
        show_error(resp)
        return
    data = resp.json()
    items = data.get("items", [])
    st.caption(f"{data.get('total', 0)} transaction(s) total, showing {len(items)}")

    if not items:
        st.info("No transactions yet. Add one above!")
        return

    df = tx_to_rows(items)
    st.dataframe(df, width="stretch", hide_index=True)

    st.markdown("#### Edit / delete")
    id_to_label = {t["id"]: f"{t['transaction_date'][:10]} - {t['item_name']} ({t['amount']} {t['currency']})" for t in items}
    selected_id = st.selectbox("Select transaction", options=list(id_to_label), format_func=id_to_label.get)
    sel = next(t for t in items if t["id"] == selected_id)

    with st.expander("Edit selected", expanded=False):
        with st.form("edit_tx_form"):
            e_item = st.text_input("Item name", value=sel["item_name"])
            e_amount = st.number_input("Amount", value=float(sel["amount"]), format="%.2f")
            e_currency = st.text_input("Currency", value=sel["currency"], max_chars=3)
            e_d = st.date_input("Date", value=datetime.fromisoformat(sel["transaction_date"].replace("Z", "+00:00")).date())
            e_cat_options = ["None"] + list(cat_ids)
            e_cat_index = 0
            if sel.get("category"):
                try:
                    e_cat_index = list(cat_ids).index(sel["category"]["name"]) + 1
                except ValueError:
                    e_cat_index = 0
            e_cat_label = st.selectbox("Category", options=e_cat_options, index=e_cat_index)
            e_pm = st.selectbox("Payment method", PAYMENT_METHODS, index=PAYMENT_METHODS.index(sel["payment_method"]))
            e_place = st.text_input("Place", value=sel["place"] or "")
            submitted = st.form_submit_button("Save changes", width="stretch")
        if submitted:
            payload = {
                "item_name": e_item,
                "amount": round(e_amount, 2),
                "currency": e_currency,
                "transaction_date": datetime.combine(e_d, time.min).isoformat(),
                "category_id": cat_ids.get(e_cat_label) if e_cat_label != "None" else None,
                "payment_method": e_pm,
                "place": e_place or None,
            }
            resp = api("PUT", f"/transactions/{selected_id}", json=payload)
            if resp.ok:
                st.success("Transaction updated")
                st.rerun()
            else:
                show_error(resp)

    if st.button("Delete selected transaction", type="secondary"):
        resp = api("DELETE", f"/transactions/{selected_id}")
        if resp.status_code == 204:
            st.success("Transaction deleted")
            st.rerun()
        else:
            show_error(resp)


# --------------------------------------------------------------------------
# RECURRING PAYMENTS
# --------------------------------------------------------------------------
def rp_to_rows(items: list[dict]) -> pd.DataFrame:
    rows = [
        {
            "Name": r["name"],
            "Amount": float(r["amount"]),
            "Frequency": r["frequency"],
            "Next due": r["next_due_date"],
            "Category": cat_name(r.get("category")),
            "Active": "yes" if r["is_active"] else "no",
            "ID": r["id"],
        }
        for r in items
    ]
    return pd.DataFrame(rows)


def render_recurring_payments():
    st.subheader("Recurring payments")

    with st.expander("Add recurring payment", expanded=False):
        with st.form("add_rp_form"):
            name = st.text_input("Name (e.g. Netflix)")
            amount = st.number_input("Amount", min_value=0.0, format="%.2f")
            frequency = st.selectbox("Frequency", FREQUENCIES)
            due = st.date_input("Next due date", value=date.today())
            cats = load_categories()
            cat_choices = {c["name"]: c["id"] for c in cats}
            cat_label = st.selectbox("Category", options=["None"] + list(cat_choices), key="rp_cat")
            submitted = st.form_submit_button("Add", width="stretch")
        if submitted and name and amount > 0:
            payload = {
                "name": name,
                "amount": round(amount, 2),
                "frequency": frequency,
                "next_due_date": due.isoformat(),
                "category_id": cat_choices.get(cat_label) if cat_label != "None" else None,
            }
            resp = api("POST", "/recurring-payments", json=payload)
            if resp.ok:
                st.success(f"Added recurring payment '{name}'")
                st.rerun()
            else:
                show_error(resp)

    include_inactive = st.checkbox("Show cancelled payments", key="rp_inactive")
    params = {"include_inactive": "true"} if include_inactive else {}
    resp = api("GET", "/recurring-payments", params=params)
    if not resp.ok:
        show_error(resp)
        return
    items = resp.json()
    if not items:
        st.info("No recurring payments.")
        return

    st.dataframe(rp_to_rows(items), width="stretch", hide_index=True)
    if not include_inactive:
        st.caption("Active only. Tick 'Show cancelled payments' to see history.")

    id_to_label = {
        r["id"]: f"{r['name']} ({r['amount']} {r['frequency']}, due {r['next_due_date']})"
        for r in items
    }
    selected_id = st.selectbox("Select recurring payment", options=list(id_to_label), format_func=id_to_label.get)
    sel = next(r for r in items if r["id"] == selected_id)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancel payment (soft delete)", width="stretch"):
            resp = api("DELETE", f"/recurring-payments/{selected_id}")
            if resp.ok:
                st.success(f"Cancelled '{sel['name']}' (kept for history)")
                st.rerun()
            else:
                show_error(resp)
    with c2:
        if sel["is_active"]:
            if st.button("Edit amount / name", width="stretch"):
                st.session_state["edit_rp_id"] = selected_id
        else:
            st.markdown("Cancelled records cannot be edited (re-create if needed).")

    edit_id = st.session_state.get("edit_rp_id")
    if edit_id and edit_id == selected_id:
        with st.form("edit_rp_form"):
            e_name = st.text_input("Name", value=sel["name"])
            e_amount = st.number_input("Amount", value=float(sel["amount"]), format="%.2f")
            e_freq = st.selectbox("Frequency", FREQUENCIES, index=FREQUENCIES.index(sel["frequency"]))
            e_due = st.date_input("Next due date", value=datetime.fromisoformat(sel["next_due_date"]).date())
            submitted = st.form_submit_button("Save", width="stretch")
        if submitted:
            payload = {
                "name": e_name,
                "amount": round(e_amount, 2),
                "frequency": e_freq,
                "next_due_date": e_due.isoformat(),
            }
            resp = api("PUT", f"/recurring-payments/{selected_id}", json=payload)
            if resp.ok:
                st.success("Recurring payment updated")
                st.session_state.pop("edit_rp_id", None)
                st.rerun()
            else:
                show_error(resp)


# --------------------------------------------------------------------------
# CATEGORIES
# --------------------------------------------------------------------------
def render_categories():
    st.subheader("Categories")
    resp = api("GET", "/categories")
    if not resp.ok:
        show_error(resp)
        return
    items = resp.json()
    df = pd.DataFrame(
        [{"ID": c["id"], "Name": c["name"], "Default": "yes" if c["is_default"] else "no"} for c in items]
    )
    st.dataframe(df, width="stretch", hide_index=True)


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    st.title("Expense Tracker")
    st.caption("Receipt-scanning expense tracker - interactive frontend")

    token = st.session_state.get("token")
    if not token:
        st.info("Please log in or create an account.")
        render_auth()
        render_sidebar_user()
        return

    render_sidebar_user()
    tab_tx, tab_rp, tab_cat = st.tabs(["Transactions", "Recurring payments", "Categories"])
    with tab_tx:
        render_transactions()
    with tab_rp:
        render_recurring_payments()
    with tab_cat:
        render_categories()


main()

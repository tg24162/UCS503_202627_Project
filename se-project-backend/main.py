import uvicorn
from fastapi import FastAPI

from routers import auth, categories, recurring_payments, transactions

app = FastAPI(title="Expense Tracker API", description="Receipt-scanning expense tracker backend")

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(recurring_payments.router)
app.include_router(categories.router)


@app.get("/")
async def root():
    return {"message": "Expense Tracker API"}


if __name__ == "__main__":
    uvicorn.run(app=app)
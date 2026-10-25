"""Intentionally faulty synthetic demonstration API. Never use real funds."""
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Synthetic Wallet API — intentionally buggy", version="0.1")


class WithdrawRequest(BaseModel):
    balance: int = Field(ge=0)
    amount: int = Field(gt=0)


@app.post("/withdraw")
def withdraw(request: WithdrawRequest):
    # Deliberate bug to be revealed by business-rule testing:
    # this endpoint fails to reject amount > balance.
    return {"approved": True, "remaining": request.balance - request.amount}

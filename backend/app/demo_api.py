"""Stateless synthetic wallet: deliberate bug by default; corrected evaluation control."""

import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


class WithdrawRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    balance: int = Field(ge=0, le=10**9, strict=True)
    amount: int = Field(gt=0, le=10**9, strict=True)


def create_demo_app(buggy: bool = True) -> FastAPI:
    demo = FastAPI(
        title="Synthetic Wallet API — " + ("intentionally buggy" if buggy else "corrected control"),
        version="0.2",
    )

    @demo.get("/health")
    def health():
        return {"status": "ok", "synthetic": True, "variant": "buggy" if buggy else "corrected"}

    @demo.post("/withdraw")
    def withdraw(request: WithdrawRequest):
        if not buggy and request.amount > request.balance:
            return JSONResponse(
                status_code=422, content={"approved": False, "remaining": request.balance}
            )
        # This branch intentionally demonstrates the overdraft bug when buggy=True.
        return {"approved": True, "remaining": request.balance - request.amount}

    return demo


variant = os.getenv("SYNTHETIC_DEMO_VARIANT", "buggy")
if variant not in {"buggy", "corrected"}:
    raise RuntimeError("SYNTHETIC_DEMO_VARIANT must be buggy or corrected")
app = create_demo_app(buggy=variant == "buggy")

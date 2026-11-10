"""Bounded, expiring local plans. Client cannot relabel fixture results as Meta."""

import threading
import time
import uuid
from collections import OrderedDict
from copy import deepcopy
from fastapi import HTTPException
from .models import GenerateResponse


class PlanStore:
    def __init__(self, capacity=20, ttl_seconds=1800, clock=time.monotonic):
        self.capacity, self.ttl, self.clock = capacity, ttl_seconds, clock
        self._plans = OrderedDict()
        self._lock = threading.Lock()

    def put(self, plan: GenerateResponse, spec: dict, rule: str) -> GenerateResponse:
        with self._lock:
            self._purge()
            saved = plan.model_copy(deep=True)
            saved.plan_id = "plan-" + uuid.uuid4().hex
            self._plans[saved.plan_id] = (self.clock(), saved, deepcopy(spec), rule)
            while len(self._plans) > self.capacity:
                self._plans.popitem(last=False)
            return saved.model_copy(deep=True)

    def _purge(self):
        for key in list(self._plans):
            if self.clock() - self._plans[key][0] >= self.ttl:
                del self._plans[key]

    def get(self, plan_id):
        with self._lock:
            self._purge()
            if plan_id not in self._plans:
                raise HTTPException(
                    status_code=404,
                    detail="Plan is missing or expired; generate and review a new plan",
                )
            _, plan, spec, rule = self._plans[plan_id]
            return plan.model_copy(deep=True), deepcopy(spec), rule


plan_store = PlanStore()

from typing import Any
from fastapi import HTTPException
from .models import AnalyzeResponse, Operation, TestPlan


def parse_openapi(spec: dict[str, Any]) -> AnalyzeResponse:
    if not isinstance(spec.get("openapi"), str) or not spec["openapi"].startswith("3."):
        raise HTTPException(status_code=422, detail="MVP requires OpenAPI 3.x JSON")
    info = spec.get("info")
    paths = spec.get("paths")
    if not isinstance(info, dict) or not isinstance(paths, dict) or not paths:
        raise HTTPException(status_code=422, detail="OpenAPI must include info and nonempty paths")
    operations: list[Operation] = []
    for path, path_item in paths.items():
        if not isinstance(path, str) or not path.startswith("/") or not isinstance(path_item, dict):
            continue
        if "post" in path_item and isinstance(path_item["post"], dict):
            operations.append(Operation(method="POST", path=path))
    if not operations:
        raise HTTPException(status_code=422, detail="MVP supports at least one POST operation")
    return AnalyzeResponse(title=str(info.get("title", "Untitled")), operations=operations)


def validate_plan_against_spec(plan: TestPlan, spec: dict[str, Any]) -> None:
    operations = parse_openapi(spec).operations
    permitted = {(op.method, op.path) for op in operations}
    if any((c.method, c.path) not in permitted for c in plan.cases):
        raise HTTPException(status_code=422, detail="Generated plan includes an undeclared operation")

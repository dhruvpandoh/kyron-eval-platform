from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core import load_scenarios, run_suite
from .db import get_run, list_runs, review_result, save_run

app = FastAPI(title="Kyron Voice Agent Evaluation Platform")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    agent_version: str


class ReviewRequest(BaseModel):
    label: str | None = None
    note: str | None = None


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/scenarios")
def scenarios():
    return load_scenarios()


@app.get("/api/runs")
def runs():
    return list_runs()


@app.post("/api/runs")
def create_run(request: RunRequest):
    if request.agent_version not in {"v1", "v2"}:
        raise HTTPException(400, "agent_version must be v1 or v2")
    output = run_suite(request.agent_version)
    run_id = save_run(output)
    return get_run(run_id)


@app.post("/api/experiment")
def create_experiment():
    ids = {}
    for version in ("v1", "v2"):
        ids[version] = save_run(run_suite(version))
    return {"v1": get_run(ids["v1"]), "v2": get_run(ids["v2"])}


@app.get("/api/runs/{run_id}")
def run_detail(run_id: int):
    result = get_run(run_id)
    if result is None:
        raise HTTPException(404, "run not found")
    return result


@app.patch("/api/results/{result_id}/review")
def review(result_id: int, request: ReviewRequest):
    review_result(result_id, request.label, request.note)
    return {"ok": True}

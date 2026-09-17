"""FastAPI service so the Angular frontend can consume the optimizer.

Start with:
    uvicorn api.main:app --reload --port 8000

Then POST the employees/projects payload to http://localhost:8000/allocate.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from allocator.models import Technology, Employee, Project, Assignment
from allocator.optimizer import AllocationProblem, OptimizationResult, optimize

app = FastAPI(
    title="AI Resource Allocator",
    description="Assigns employees to projects maximizing utilization and profit.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AllocationRequest(BaseModel):
    technologies: list[Technology] = Field(default_factory=list)
    employees: list[Employee] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    assignments: list[Assignment] = Field(default_factory=list)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/allocate")
def allocate(req: AllocationRequest) -> dict:
    problem = AllocationProblem(
        employees=req.employees,
        projects=req.projects,
        assignments=req.assignments,
    )
    result: OptimizationResult = optimize(problem)
    return result.to_dict()
"""Data models.

These mirror the TypeScript interfaces used by the Angular frontend
(Assignment, EmployeeTechnology, Employee, Project, Technology) plus two
optional monetary fields that drive the profit optimization:

  * Employee.costPerDay  -> daily cost of the employee (default 200)
  * Project.dailyRate    -> daily revenue billed for the project (default 1000)
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProficiencyLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class AssignmentMode(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"


class ProjectStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PLANNED = "PLANNED"
    COMPLETED = "COMPLETED"


class Technology(BaseModel):
    id: int
    name: str
    category: str
    version: str
    description: str = ""


class EmployeeTechnology(BaseModel):
    technologyId: int
    level: ProficiencyLevel = ProficiencyLevel.BEGINNER
    version: str
    yearsExperience: float = 0


class Employee(BaseModel):
    id: int
    firstName: str
    lastName: str
    email: str
    position: str
    hireDate: date
    technologies: list[EmployeeTechnology] = Field(default_factory=list)
    costPerDay: float = 200


class ProjectTechnologyRequirement(BaseModel):
    technologyId: int
    version: str
    minLevel: ProficiencyLevel = ProficiencyLevel.BEGINNER
    minYearsExperience: float = 0
    count: int = 1

    @field_validator("count", mode="before")
    @classmethod
    def _count_or_default(cls, v: object) -> int:
        return 1 if v is None else v


class Project(BaseModel):
    id: int
    name: str
    description: str = ""
    client: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    startDate: date
    endDate: date
    requiredTechnologies: list[ProjectTechnologyRequirement] = Field(
        default_factory=list
    )
    dailyRate: float = 1000


class Assignment(BaseModel):
    id: int
    employeeId: int
    projectId: int
    mode: AssignmentMode = AssignmentMode.FULL_TIME
    hoursPerDay: float = 8
    startDate: date
    endDate: date
    notes: str = ""


class OptimizationInput(BaseModel):
    technologies: list[Technology] = Field(default_factory=list)
    employees: list[Employee] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    assignments: list[Assignment] = Field(default_factory=list)
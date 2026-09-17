"""AI-driven resource allocation optimizer."""

from .models import (
    Assignment,
    AssignmentMode,
    Employee,
    EmployeeTechnology,
    ProficiencyLevel,
    Project,
    ProjectStatus,
    ProjectTechnologyRequirement,
    Technology,
)
from .optimizer import AllocationProblem, OptimizationResult, optimize

__version__ = "0.1.0"

__all__ = [
    "AllocationProblem",
    "Assignment",
    "AssignmentMode",
    "Employee",
    "EmployeeTechnology",
    "OptimizationResult",
    "ProficiencyLevel",
    "Project",
    "ProjectStatus",
    "ProjectTechnologyRequirement",
    "Technology",
    "optimize",
]
"""Generate a realistic sample dataset for development/testing."""
from __future__ import annotations

import json
from datetime import date, timedelta

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


def build_sample(today: date | None = None) -> dict:
    today = today or date.today()
    d = lambda n: today + timedelta(days=n)  # noqa: E731

    technologies = [
        Technology(id=1, name="TypeScript", category="Language", version="5.4"),
        Technology(id=2, name="Angular", category="Framework", version="18.2"),
        Technology(id=3, name="React", category="Framework", version="18.3"),
        Technology(id=4, name="Node.js", category="Runtime", version="20.11"),
        Technology(id=5, name="Python", category="Language", version="3.12"),
        Technology(id=6, name="SQL", category="Database", version="15"),
        Technology(id=7, name="Java", category="Language", version="21"),
        Technology(id=8, name="Docker", category="DevOps", version="26"),
        Technology(id=9, name="AWS", category="Cloud", version="2024"),
        Technology(id=10, name="Kubernetes", category="DevOps", version="1.30"),
    ]

    def et(tid, level, version, years):
        return EmployeeTechnology(
            technologyId=tid, level=level, version=version, yearsExperience=years
        )

    employees = [
        Employee(
            id=1, firstName="Ana", lastName="García", email="ana.garcia@corp.com",
            position="Senior Frontend", hireDate=date(2020, 3, 1), costPerDay=350,
            technologies=[
                et(2, ProficiencyLevel.EXPERT, "18.2", 5),
                et(1, ProficiencyLevel.ADVANCED, "5.4", 5),
                et(4, ProficiencyLevel.INTERMEDIATE, "20.11", 3),
            ],
        ),
        Employee(
            id=2, firstName="Luis", lastName="Pérez", email="luis.perez@corp.com",
            position="Fullstack", hireDate=date(2021, 7, 12), costPerDay=280,
            technologies=[
                et(1, ProficiencyLevel.ADVANCED, "5.4", 4),
                et(4, ProficiencyLevel.ADVANCED, "20.11", 4),
                et(6, ProficiencyLevel.INTERMEDIATE, "15", 3),
            ],
        ),
        Employee(
            id=3, firstName="María", lastName="López", email="maria.lopez@corp.com",
            position="Backend", hireDate=date(2019, 11, 5), costPerDay=320,
            technologies=[
                et(5, ProficiencyLevel.EXPERT, "3.12", 6),
                et(6, ProficiencyLevel.ADVANCED, "15", 6),
                et(8, ProficiencyLevel.INTERMEDIATE, "26", 2),
                et(9, ProficiencyLevel.INTERMEDIATE, "2024", 2),
            ],
        ),
        Employee(
            id=4, firstName="Carlos", lastName="Ruíz", email="carlos.ruiz@corp.com",
            position="ML Engineer", hireDate=date(2022, 2, 15), costPerDay=380,
            technologies=[
                et(5, ProficiencyLevel.ADVANCED, "3.12", 4),
                et(9, ProficiencyLevel.INTERMEDIATE, "2024", 2),
                et(6, ProficiencyLevel.INTERMEDIATE, "15", 3),
            ],
        ),
        Employee(
            id=5, firstName="Sofía", lastName="Martínez", email="sofia.martinez@corp.com",
            position="Frontend", hireDate=date(2023, 5, 20), costPerDay=220,
            technologies=[
                et(3, ProficiencyLevel.ADVANCED, "18.3", 3),
                et(1, ProficiencyLevel.INTERMEDIATE, "5.4", 2),
            ],
        ),
        Employee(
            id=6, firstName="Diego", lastName="Sánchez", email="diego.sanchez@corp.com",
            position="DevOps", hireDate=date(2021, 9, 8), costPerDay=310,
            technologies=[
                et(8, ProficiencyLevel.ADVANCED, "26", 4),
                et(10, ProficiencyLevel.INTERMEDIATE, "1.30", 2),
                et(9, ProficiencyLevel.ADVANCED, "2024", 3),
            ],
        ),
        Employee(
            id=7, firstName="Laura", lastName="Torres", email="laura.torres@corp.com",
            position="Java Engineer", hireDate=date(2018, 4, 2), costPerDay=330,
            technologies=[
                et(7, ProficiencyLevel.EXPERT, "21", 7),
                et(6, ProficiencyLevel.ADVANCED, "15", 6),
                et(8, ProficiencyLevel.BEGINNER, "26", 1),
            ],
        ),
        Employee(
            id=8, firstName="Javier", lastName="Mendoza", email="javier.mendoza@corp.com",
            position="Frontend Junior", hireDate=date(2024, 1, 15), costPerDay=180,
            technologies=[
                et(2, ProficiencyLevel.INTERMEDIATE, "18.2", 1),
                et(1, ProficiencyLevel.BEGINNER, "5.4", 1),
            ],
        ),
    ]

    projects = [
        Project(
            id=1, name="Portal Bancario", description="Portal web del banco",
            client="Banco Central", status=ProjectStatus.ACTIVE,
            startDate=d(-20), endDate=d(120), dailyRate=1800,
            requiredTechnologies=[
                ProjectTechnologyRequirement(
                    technologyId=2, version="18.2", minLevel=ProficiencyLevel.ADVANCED,
                    minYearsExperience=2, count=2,
                ),
                ProjectTechnologyRequirement(
                    technologyId=1, version="5.4", minLevel=ProficiencyLevel.INTERMEDIATE,
                    minYearsExperience=1, count=2,
                ),
            ],
        ),
        Project(
            id=2, name="Motor de Riesgo", description="Motor de scoring crediticio",
            client="FinanzaPlus", status=ProjectStatus.ACTIVE,
            startDate=d(-10), endDate=d(90), dailyRate=2200,
            requiredTechnologies=[
                ProjectTechnologyRequirement(
                    technologyId=5, version="3.12", minLevel=ProficiencyLevel.ADVANCED,
                    minYearsExperience=3, count=2,
                ),
                ProjectTechnologyRequirement(
                    technologyId=9, version="2024", minLevel=ProficiencyLevel.INTERMEDIATE,
                    minYearsExperience=1, count=1,
                ),
            ],
        ),
        Project(
            id=3, name="App Retail", description="App e-commerce de retail",
            client="TiendaMax", status=ProjectStatus.ACTIVE,
            startDate=d(5), endDate=d(45), dailyRate=1500,
            requiredTechnologies=[
                ProjectTechnologyRequirement(
                    technologyId=3, version="18.3", minLevel=ProficiencyLevel.INTERMEDIATE,
                    minYearsExperience=1, count=1,
                ),
                ProjectTechnologyRequirement(
                    technologyId=1, version="5.4", minLevel=ProficiencyLevel.BEGINNER,
                    count=1,
                ),
            ],
        ),
        Project(
            id=4, name="Migración Cloud", description="Migración a AWS/K8s",
            client="LogiCorp", status=ProjectStatus.PLANNED,
            startDate=d(15), endDate=d(75), dailyRate=2600,
            requiredTechnologies=[
                ProjectTechnologyRequirement(
                    technologyId=8, version="26", minLevel=ProficiencyLevel.ADVANCED,
                    minYearsExperience=2, count=1,
                ),
                ProjectTechnologyRequirement(
                    technologyId=10, version="1.30", minLevel=ProficiencyLevel.INTERMEDIATE,
                    count=1,
                ),
            ],
        ),
        Project(
            id=5, name="Mantenimiento Core", description="Soporte sistemas legados",
            client="CoreSeguros", status=ProjectStatus.ACTIVE,
            startDate=d(30), endDate=d(60), dailyRate=1400,
            requiredTechnologies=[
                ProjectTechnologyRequirement(
                    technologyId=7, version="21", minLevel=ProficiencyLevel.ADVANCED,
                    minYearsExperience=3, count=1,
                ),
                ProjectTechnologyRequirement(
                    technologyId=6, version="15", minLevel=ProficiencyLevel.INTERMEDIATE,
                    count=1,
                ),
            ],
        ),
    ]

    assignments = [
        # Ana is currently assigned to Portal Bancario until day 40.
        Assignment(
            id=1, employeeId=1, projectId=1, mode=AssignmentMode.FULL_TIME,
            startDate=d(-20), endDate=d(40),
        ),
        # María currently on Motor de Riesgo until day 25.
        Assignment(
            id=2, employeeId=3, projectId=2, mode=AssignmentMode.FULL_TIME,
            startDate=d(-10), endDate=d(25),
        ),
    ]

    # quiet warnings in heavy editors about unused enums
    _ = AssignmentMode.FULL_TIME

    return {
        "technologies": [t.model_dump(mode="json") for t in technologies],
        "employees": [e.model_dump(mode="json") for e in employees],
        "projects": [p.model_dump(mode="json") for p in projects],
        "assignments": [a.model_dump(mode="json") for a in assignments],
    }


def save_sample(path: str, today: date | None = None) -> str:
    data = build_sample(today)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return path
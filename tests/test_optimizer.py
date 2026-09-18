import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from allocator.generate import build_sample  # noqa: E402
from allocator.models import (  # noqa: E402
    Assignment,
    Employee,
    EmployeeTechnology,
    OptimizationInput,
    ProficiencyLevel,
    Project,
    ProjectTechnologyRequirement,
    Technology,
)
from allocator.optimizer import AllocationProblem, optimize, version_compatible  # noqa: E402

TODAY = date(2026, 9, 16)


def _employee(eid: int, techs: list[EmployeeTechnology], cost: float = 200) -> Employee:
    return Employee(
        id=eid,
        firstName="A",
        lastName=f"E{eid}",
        email=f"e{eid}@corp.com",
        position="Engineer",
        hireDate=date(2020, 1, 1),
        technologies=techs,
        costPerDay=cost,
    )


def _tech(tid: int, version: str, level=ProficiencyLevel.ADVANCED, years=3) -> EmployeeTechnology:
    return EmployeeTechnology(
        technologyId=tid, level=level, version=version, yearsExperience=years
    )


def _project(
    pid: int,
    start: date,
    end: date,
    reqs: list[ProjectTechnologyRequirement],
    rate: float = 1000,
) -> Project:
    return Project(
        id=pid,
        name=f"P{pid}",
        client="Client",
        startDate=start,
        endDate=end,
        requiredTechnologies=reqs,
        dailyRate=rate,
    )


def _req(tid: int, version: str, count: int = 1, level=ProficiencyLevel.BEGINNER) -> ProjectTechnologyRequirement:
    return ProjectTechnologyRequirement(
        technologyId=tid, version=version, count=count, minLevel=level
    )


class TestVersionCompatibility(unittest.TestCase):
    def test_exact(self):
        self.assertTrue(version_compatible("18.2", "18.2"))
        self.assertTrue(version_compatible("5.4", "5.4"))

    def test_same_major_newer(self):
        self.assertTrue(version_compatible("18.5", "18.2"))
        self.assertTrue(version_compatible("20.12", "20.11"))

    def test_wrong_major(self):
        self.assertFalse(version_compatible("17.0", "18.2"))
        self.assertFalse(version_compatible("19.0", "18.2"))

    def test_older_minor(self):
        self.assertFalse(version_compatible("18.1", "18.2"))


class TestOptimizer(unittest.TestCase):
    def _run(self, employees, projects, assignments=()):
        problem = AllocationProblem(
            employees=employees, projects=projects, assignments=list(assignments), today=TODAY
        )
        return optimize(problem)

    def test_single_match_fills_horizon(self):
        emp = _employee(1, [_tech(1, "18.2")])
        proj = _project(1, TODAY, TODAY + timedelta(days=10), [_req(1, "18.2")])
        res = self._run([emp], [proj])
        self.assertEqual(len(res.assignments), 1)
        a = res.assignments[0]
        self.assertEqual(a.startDate, TODAY)
        self.assertEqual(a.endDate, TODAY + timedelta(days=10))
        self.assertGreater(res.summary["totalProfit"], 0)
        self.assertEqual(res.summary["idleEmployees"], 0)

    def test_level_too_low_rejected(self):
        emp = _employee(1, [_tech(1, "18.2", level=ProficiencyLevel.BEGINNER, years=0)])
        proj = _project(
            1, TODAY, TODAY + timedelta(days=10),
            [_req(1, "18.2", level=ProficiencyLevel.ADVANCED)],
        )
        res = self._run([emp], [proj])
        self.assertEqual(len(res.assignments), 0)
        self.assertEqual(res.summary["occupiedEmployees"], 0)

    def test_no_double_booking(self):
        # Two projects, only one employee -> never on both same day.
        emp = _employee(1, [_tech(1, "18.2")])
        p1 = _project(1, TODAY, TODAY + timedelta(days=10), [_req(1, "18.2")])
        p2 = _project(2, TODAY, TODAY + timedelta(days=10), [_req(1, "18.2")])
        res = self._run([emp], [p1, p2])
        for a in res.assignments:
            self.assertEqual(a.employeeId, 1)
        days = set()
        for a in res.assignments:
            d = a.startDate
            while d <= a.endDate:
                self.assertNotIn(d, days, "employee double booked")
                days.add(d)
                d += timedelta(days=1)

    def test_current_assignment_respected(self):
        emp = _employee(1, [_tech(1, "18.2")])
        proj = _project(1, TODAY, TODAY + timedelta(days=30), [_req(1, "18.2")])
        existing = Assignment(
            id=1, employeeId=1, projectId=1,
            startDate=TODAY, endDate=TODAY + timedelta(days=9),
        )
        res = self._run([emp], [proj], [existing])
        # kept current assignment + a follow-on booking that picks up after it
        self.assertEqual(len(res.assignments), 2)
        follow_ons = [a for a in res.assignments if a.id != existing.id]
        self.assertEqual(len(follow_ons), 1)
        a = follow_ons[0]
        # must not overlap the existing assignment
        self.assertGreaterEqual(a.startDate, TODAY + timedelta(days=10))

    def test_capacity_limit(self):
        # project needs only 1 Angular dev; 2 employees -> 1 used.
        e1 = _employee(1, [_tech(1, "18.2")])
        e2 = _employee(2, [_tech(1, "18.2")])
        proj = _project(1, TODAY, TODAY + timedelta(days=5), [_req(1, "18.2", count=1)])
        res = self._run([e1, e2], [proj])
        proj_days = sum(
            1
            for a in res.assignments
            if a.projectId == 1 and a.startDate <= TODAY + timedelta(days=2) <= a.endDate
        )
        self.assertLessEqual(proj_days, 1)

    def test_version_gap_rejected(self):
        emp = _employee(1, [_tech(1, "17.0")])
        proj = _project(1, TODAY, TODAY + timedelta(days=5), [_req(1, "18.2")])
        res = self._run([emp], [proj])
        self.assertEqual(len(res.assignments), 0)

    def test_null_count_treated_as_one(self):
        # The backend seeds requirement `count` as null (unset);
        # the optimizer must accept it and fall back to a single slot.
        data = {
            "projects": [{
                "id": 1,
                "name": "P1",
                "startDate": TODAY.isoformat(),
                "endDate": (TODAY + timedelta(days=5)).isoformat(),
                "requiredTechnologies": [
                    {"technologyId": 1, "version": "18.2", "count": None}
                ],
            }]
        }
        parsed = OptimizationInput.model_validate(data)
        req = parsed.projects[0].requiredTechnologies[0]
        self.assertEqual(req.count, 1)

        emp = _employee(1, [_tech(1, "18.2")])
        proj = _project(1, TODAY, TODAY + timedelta(days=5), [_req(1, "18.2", count=1)])
        res = self._run([emp], [proj])
        self.assertEqual(len(res.assignments), 1)


class TestSample(unittest.TestCase):
    def test_sample_runs(self):
        data = build_sample(TODAY)
        parsed = OptimizationInput.model_validate(data)
        problem = AllocationProblem(
            employees=parsed.employees,
            projects=parsed.projects,
            assignments=parsed.assignments,
            today=TODAY,
        )
        res = optimize(problem)
        self.assertGreater(res.summary["occupiedEmployees"], 0)
        self.assertGreater(res.summary["totalProfit"], 0)
        self.assertEqual(res.summary["today"], TODAY.isoformat())


if __name__ == "__main__":
    unittest.main()
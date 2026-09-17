"""AI-driven allocation optimizer.

Hybrid heuristic pipeline:

1. Feasibility filtering  - an employee qualifies for a project slot only
   when their technology matches the requirement (technology, version,
   proficiency level and years of experience).
2. Profit-ranked greedy   - candidates are scheduled in descending marginal
   profit so the most valuable (project dailyRate - employee cost) pairs
   are booked first over their valid windows.
3. Gap filling            - employees who still have idle days are assigned
   to any remaining qualifying project so nobody sits unassigned.
4. Local search           - a bounded exchange pass moves employees to higher
   profit projects when feasible, improving total monetary gain.

Invariants guaranteed after every step:
  * an employee is never double-booked on a single day,
  * a project slot is never filled beyond its capacity,
  * every assignment respects technology / version / level / experience
    requirements and the project's active window.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable, Optional

from .models import (
    Assignment,
    AssignmentMode,
    Employee,
    ProficiencyLevel,
    Project,
    ProjectStatus,
    ProjectTechnologyRequirement,
)

LEVEL_WEIGHT = {
    ProficiencyLevel.BEGINNER: 1,
    ProficiencyLevel.INTERMEDIATE: 2,
    ProficiencyLevel.ADVANCED: 3,
    ProficiencyLevel.EXPERT: 4,
}

FULL_TIME_HOURS = 8.0


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------
def _components(version: str) -> list[int]:
    try:
        return [int(p) for p in version.strip().split(".")]
    except (ValueError, AttributeError):
        return [0]


def _leq(a: list[int], b: list[int]) -> bool:
    a = (a + [0, 0])[:3]
    b = (b + [0, 0])[:3]
    return a <= b


def version_compatible(employee_version: str, required_version: str) -> bool:
    """Same major version and employee version >= required (or exact match)."""
    emp = _components(employee_version)
    req = _components(required_version)
    if not emp or not req:
        return False
    if emp[0] != req[0]:
        return False
    return _leq(req, emp)


def _days(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def _daily_profit(project: Project, employee: Employee, hours_per_day: float) -> float:
    return max(0.0, (project.dailyRate - employee.costPerDay) * (hours_per_day / FULL_TIME_HOURS))


def _slot_key(project_id: int, req_index: int, slot_index: int) -> tuple:
    return (project_id, req_index, slot_index)


def _employee_feasible_for_requirement(
    employee: Employee, requirement: ProjectTechnologyRequirement
) -> bool:
    for tech in employee.technologies:
        if tech.technologyId != requirement.technologyId:
            continue
        if not version_compatible(tech.version, requirement.version):
            continue
        if LEVEL_WEIGHT[tech.level] < LEVEL_WEIGHT[requirement.minLevel]:
            continue
        if tech.yearsExperience < requirement.minYearsExperience:
            continue
        return True
    return False


@dataclass
class Block:
    """A booked unit: an employee covering a single project slot for days."""

    assignment: Assignment
    slot_key: tuple


# ---------------------------------------------------------------------------
# Problem / result
# ---------------------------------------------------------------------------
@dataclass
class AllocationProblem:
    employees: list[Employee]
    projects: list[Project]
    assignments: list[Assignment] = field(default_factory=list)
    today: Optional[date] = None

    def __post_init__(self) -> None:
        if self.today is None:
            self.today = date.today()


@dataclass
class OptimizationResult:
    assignments: list[Assignment]
    summary: dict
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "assignments": [a.model_dump(mode="json") for a in self.assignments],
            "summary": self.summary,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------
def optimize(problem: AllocationProblem) -> OptimizationResult:
    today = problem.today
    warnings: list[str] = []

    employee_map = {e.id: e for e in problem.employees}
    project_map = {p.id: p for p in problem.projects}
    projects = [
        p for p in problem.projects
        if p.status != ProjectStatus.COMPLETED and p.endDate >= today
    ]
    if not projects:
        warnings.append("No active projects to allocate employees into.")

    horizon_end = max([p.endDate for p in projects] + [today])
    for a in problem.assignments:
        if a.endDate > horizon_end:
            horizon_end = a.endDate

    # Employees blocked until their current assignment ends.
    kept: dict[int, Assignment] = {}
    busy: dict[int, set[date]] = {e.id: set() for e in problem.employees}
    available_from: dict[int, date] = {}

    for e in problem.employees:
        eid = e.id
        active = sorted(
            (a for a in problem.assignments if a.employeeId == eid and a.endDate >= today),
            key=lambda a: a.endDate,
        )
        if active:
            last = active[-1]
            kept[eid] = last
            available_from[eid] = last.endDate + timedelta(days=1)
            for d in _days(max(today, last.startDate), last.endDate):
                busy[eid].add(d)
        else:
            available_from[eid] = today

    # Slot coverage: (project, req index, slot index) -> covered days.
    slot_cover: dict[tuple, set[date]] = {}
    for p in projects:
        for req_index, req in enumerate(p.requiredTechnologies):
            for s in range(req.count):
                slot_cover.setdefault(_slot_key(p.id, req_index, s), set())

    def cover_existing(assignment: Assignment) -> None:
        p = project_map.get(assignment.projectId)
        if p is None or assignment.employeeId not in employee_map:
            return
        emp = employee_map[assignment.employeeId]
        for req_index, req in enumerate(p.requiredTechnologies):
            if not _employee_feasible_for_requirement(emp, req):
                continue
            for s in range(req.count):
                key = _slot_key(p.id, req_index, s)
                days = set(_days(assignment.startDate, assignment.endDate))
                days = {d for d in days if d >= today and d <= p.endDate}
                free = days - set(slot_cover[key])
                if free:
                    slot_cover[key].update(free)
                    return

    for a in problem.assignments:
        cover_existing(a)
        if a.employeeId in busy:
            busy[a.employeeId].update(
                d for d in _days(a.startDate, a.endDate) if today <= d <= horizon_end
            )

    # ------------------------------------------------------------------
    # Candidates
    # ------------------------------------------------------------------
    candidates: list[dict] = []
    for e in problem.employees:
        eid = e.id
        aff = available_from.get(eid, today)
        if aff > horizon_end:
            continue
        for p in projects:
            ws = max(aff, p.startDate)
            we = min(horizon_end, p.endDate)
            if ws > we:
                continue
            profit = _daily_profit(p, e, FULL_TIME_HOURS)
            for req_index, req in enumerate(p.requiredTechnologies):
                if not _employee_feasible_for_requirement(e, req):
                    continue
                for s in range(req.count):
                    candidates.append(
                        {
                            "employee": e,
                            "project": p,
                            "slot_key": _slot_key(p.id, req_index, s),
                            "profit_per_day": profit,
                            "start": ws,
                            "end": we,
                        }
                    )

    # Most profitable first; among equal profit, the least flexible employee
    # (shortest window) goes first so they still get a spot.
    candidates.sort(
        key=lambda c: (
            -c["profit_per_day"],
            (c["end"] - c["start"]).days,
            c["employee"].id,
        )
    )

    # ------------------------------------------------------------------
    # Greedy scheduling
    # ------------------------------------------------------------------
    plan: dict[int, list[Block]] = {}
    next_id = max([a.id for a in problem.assignments] + [0]) + 1

    def longest_free_run(emp_id: int, cand: dict) -> Optional[tuple[date, date]]:
        start, end = cand["start"], cand["end"]
        emp_busy = busy.get(emp_id, set())
        slot = slot_cover.get(cand["slot_key"], set())
        best: Optional[tuple[date, date]] = None
        cur_start: Optional[date] = None
        cur = start
        while cur <= end:
            free = cur not in emp_busy and cur not in slot
            if free and cur_start is None:
                cur_start = cur
            if not free and cur_start is not None:
                if best is None or (cur - cur_start) > (best[1] - best[0]):
                    best = (cur_start, cur - timedelta(days=1))
                cur_start = None
            cur += timedelta(days=1)
        if cur_start is not None:
            if best is None or (end - cur_start) > (best[1] - best[0]):
                best = (cur_start, end)
        return best

    def book(emp_id: int, cand: dict, start: date, end: date) -> None:
        key = cand["slot_key"]
        for d in _days(start, end):
            busy.setdefault(emp_id, set()).add(d)
            slot_cover.setdefault(key, set()).add(d)
        assignment = Assignment(
            id=next_id,
            employeeId=emp_id,
            projectId=cand["project"].id,
            mode=AssignmentMode.FULL_TIME,
            hoursPerDay=FULL_TIME_HOURS,
            startDate=start,
            endDate=end,
            notes="auto-assigned",
        )
        plan.setdefault(emp_id, []).append(Block(assignment=assignment, slot_key=key))

    for cand in candidates:
        eid = cand["employee"].id
        run = longest_free_run(eid, cand)
        if run is None:
            continue
        book(eid, cand, run[0], run[1])

    # ------------------------------------------------------------------
    # Gap filling: reduce idle time wherever a project still needs skills.
    # ------------------------------------------------------------------
    for _ in range(2):
        changed = False
        for eid in sorted(employee_map):
            for cand in candidates:
                if cand["employee"].id != eid:
                    continue
                run = longest_free_run(eid, cand)
                if run is None:
                    continue
                book(eid, cand, run[0], run[1])
                changed = True
        if not changed:
            break

    # ------------------------------------------------------------------
    # Local search: exchange lower-profit bookings for higher-profit ones.
    # ------------------------------------------------------------------
    def profit_days(block: Block) -> float:
        emp = employee_map[block.assignment.employeeId]
        p = project_map[block.assignment.projectId]
        n = len(set(_days(block.assignment.startDate, block.assignment.endDate)))
        return _daily_profit(p, emp, block.assignment.hoursPerDay) * n

    for _ in range(300):
        best_gain = 0.0
        best_move = None
        for eid, blocks in list(plan.items()):
            for b in blocks:
                a = b.assignment
                cur_p = project_map[a.projectId]
                existing_run = set(_days(a.startDate, a.endDate))
                for cand in candidates:
                    if cand["employee"].id != eid:
                        continue
                    if cand["project"].id == a.projectId:
                        continue
                    ws = max(a.startDate, cand["start"])
                    we = min(a.endDate, cand["end"])
                    if ws > we:
                        continue
                    overlap = set(_days(ws, we))
                    if not overlap:
                        continue
                    slot = slot_cover.get(cand["slot_key"], set())
                    if overlap & slot:
                        continue
                    gain = (cand["profit_per_day"] - _daily_profit(cur_p, employee_map[eid], a.hoursPerDay)) * len(overlap)
                    if gain > best_gain:
                        best_gain = gain
                        best_move = (eid, b, cand, ws, we, overlap)
        if best_move is None or best_gain <= 0:
            break
        eid, old_block, cand, ws, we, overlap = best_move
        a = old_block.assignment

        # 1. remove `overlap` days from old booking (split if needed)
        left = []
        right = []
        if a.startDate < ws:
            left = [Block(
                Assignment(
                    id=next_id, employeeId=a.employeeId, projectId=a.projectId,
                    mode=a.mode, hoursPerDay=a.hoursPerDay,
                    startDate=a.startDate, endDate=ws - timedelta(days=1), notes=a.notes,
                ),
                old_block.slot_key,
            )]
        if we < a.endDate:
            right = [Block(
                Assignment(
                    id=next_id, employeeId=a.employeeId, projectId=a.projectId,
                    mode=a.mode, hoursPerDay=a.hoursPerDay,
                    startDate=we + timedelta(days=1), endDate=a.endDate, notes=a.notes,
                ),
                old_block.slot_key,
            )]
        plan[eid].remove(old_block)
        # free the moved days
        for d in overlap:
            busy.setdefault(eid, set()).discard(d)
            slot_cover.get(old_block.slot_key, set()).discard(d)
        # 2. book new
        book(eid, cand, ws, we)
        # 3. reassemble leftovers
        plan.setdefault(eid, []).extend(left + right)

    # ------------------------------------------------------------------
    # Output: kept current assignments + fresh plan
    # ------------------------------------------------------------------
    final_assignments: list[Assignment] = sorted(kept.values(), key=lambda x: x.id)
    for eid in sorted(plan):
        for b in plan[eid]:
            b.assignment.id = next_id
            next_id += 1
            final_assignments.append(b.assignment)
    final_assignments.sort(key=lambda x: (x.employeeId, x.startDate))

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    total_days = 0
    total_profit = 0.0
    occupied: set[int] = set()
    per_employee: dict[int, int] = {e.id: 0 for e in problem.employees}
    per_project: dict[int, int] = {p.id: 0 for p in projects}
    available_days: dict[int, int] = {}
    for e in problem.employees:
        available_days[e.id] = len(
            set(_days(available_from.get(e.id, today), horizon_end))
        )

    for a in final_assignments:
        p = project_map.get(a.projectId)
        if p is None or a.employeeId not in employee_map:
            continue
        n = len({d for d in _days(a.startDate, a.endDate) if today <= d <= horizon_end})
        emp = employee_map[a.employeeId]
        if n > 0:
            total_days += n
            total_profit += _daily_profit(p, emp, a.hoursPerDay) * n
            occupied.add(a.employeeId)
            per_employee[a.employeeId] = per_employee.get(a.employeeId, 0) + n
            per_project[p.id] = per_project.get(p.id, 0) + n

    def utilization(eid: int) -> float:
        avail = available_days.get(eid, 0)
        return 0.0 if avail == 0 else min(1.0, per_employee.get(eid, 0) / avail)

    avg_util = (
        sum(utilization(e.id) for e in problem.employees) / len(problem.employees)
        if problem.employees
        else 0.0
    )

    summary = {
        "today": today.isoformat(),
        "horizonEnd": horizon_end.isoformat(),
        "totalEmployees": len(problem.employees),
        "totalProjects": len(projects),
        "occupiedEmployees": len(occupied),
        "idleEmployees": len(problem.employees) - len(occupied),
        "totalAssignedDays": total_days,
        "averageUtilization": round(avg_util, 4),
        "utilization": {eid: round(utilization(eid), 4) for eid in employee_map},
        "totalProfit": round(total_profit, 2),
        "employeeDaysAvailable": available_days,
        "perProjectDays": per_project,
    }

    return OptimizationResult(
        assignments=final_assignments, summary=summary, warnings=warnings
    )


def optimize_from_json(data: dict) -> OptimizationResult:
    from .models import OptimizationInput

    parsed = OptimizationInput.model_validate(data)
    problem = AllocationProblem(
        employees=parsed.employees,
        projects=parsed.projects,
        assignments=parsed.assignments,
    )
    return optimize(problem)
from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class AssignmentStatus(StrEnum):
    ACTIVE = "Đang cấp phát"
    RETURNED = "Đã thu hồi"


@dataclass
class Assignment:
    assignment_id: str
    asset_code: str
    employee_id: str
    issued_on: date
    due_on: date | None = None
    returned_on: date | None = None
    return_condition: str | None = None
    status: AssignmentStatus = AssignmentStatus.ACTIVE


class AssignmentModel:
    def __init__(self) -> None:
        self._assignments: dict[str, Assignment] = {}

    def assign(self, assignment: Assignment) -> None:
        if assignment.assignment_id in self._assignments:
            raise ValueError(f"Mã cấp phát '{assignment.assignment_id}' đã tồn tại.")
        if any(
            item.asset_code == assignment.asset_code and item.status == AssignmentStatus.ACTIVE
            for item in self._assignments.values()
        ):
            raise ValueError(f"Tài sản '{assignment.asset_code}' đang được cấp phát.")
        self._assignments[assignment.assignment_id] = assignment

    def return_asset(self, assignment_id: str, returned_on: date, condition: str) -> Assignment:
        assignment = self._get(assignment_id)
        if assignment.status == AssignmentStatus.RETURNED:
            raise ValueError("Thiết bị đã được thu hồi.")
        if not condition.strip():
            raise ValueError("Cần ghi nhận tình trạng thiết bị khi thu hồi.")
        assignment.returned_on = returned_on
        assignment.return_condition = condition
        assignment.status = AssignmentStatus.RETURNED
        return assignment

    def history_for_asset(self, asset_code: str) -> tuple[Assignment, ...]:
        return tuple(item for item in self._assignments.values() if item.asset_code == asset_code)

    def history_for_employee(self, employee_id: str) -> tuple[Assignment, ...]:
        return tuple(item for item in self._assignments.values() if item.employee_id == employee_id)

    def overdue(self, today: date) -> tuple[Assignment, ...]:
        return tuple(
            item for item in self._assignments.values()
            if item.status == AssignmentStatus.ACTIVE and item.due_on is not None and item.due_on < today
        )

    def active_for_employee(self, employee_id: str) -> tuple[Assignment, ...]:
        return tuple(
            item for item in self.history_for_employee(employee_id)
            if item.status == AssignmentStatus.ACTIVE
        )

    def _get(self, assignment_id: str) -> Assignment:
        try:
            return self._assignments[assignment_id]
        except KeyError as error:
            raise KeyError(f"Không tìm thấy phiếu cấp phát '{assignment_id}'.") from error

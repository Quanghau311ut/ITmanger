from collections.abc import Sequence

from modules.assignment.models import Assignment


class AssignmentView:
    @staticmethod
    def render_history(assignments: Sequence[Assignment]) -> str:
        if not assignments:
            return "Chưa có lịch sử cấp phát."
        return "\n".join(
            f"{item.assignment_id} | {item.asset_code} | {item.employee_id} | "
            f"{item.issued_on} | {item.status.value}"
            for item in assignments
        )

from collections.abc import Sequence

from modules.employee.models import Employee


class EmployeeView:
    @staticmethod
    def render_employees(employees: Sequence[Employee]) -> str:
        if not employees:
            return "Chưa có nhân viên."
        return "\n".join(
            f"{item.employee_id} | {item.full_name} | {item.department} | "
            f"{item.email} | {item.status.value}"
            for item in employees
        )

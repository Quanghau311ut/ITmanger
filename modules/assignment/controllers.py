from datetime import date

from modules.assignment.models import Assignment, AssignmentModel
from modules.assignment.views import AssignmentView


class AssignmentController:
    def __init__(self, model: AssignmentModel, view: AssignmentView) -> None:
        self._model = model
        self._view = view

    def assign(self, assignment: Assignment) -> None:
        self._model.assign(assignment)

    def return_asset(self, assignment_id: str, returned_on: date, condition: str) -> Assignment:
        return self._model.return_asset(assignment_id, returned_on, condition)

    def employee_history(self, employee_id: str) -> str:
        return self._view.render_history(self._model.history_for_employee(employee_id))

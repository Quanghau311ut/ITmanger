from modules.employee.models import Employee, EmployeeModel
from modules.employee.views import EmployeeView


class EmployeeController:
    def __init__(self, model: EmployeeModel, view: EmployeeView) -> None:
        self._model = model
        self._view = view

    def save_employee(self, employee: Employee) -> None:
        self._model.save_employee(employee)

    def list_employees(self) -> str:
        return self._view.render_employees(self._model.employees())

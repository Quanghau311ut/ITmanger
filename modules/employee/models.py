from dataclasses import dataclass
from enum import StrEnum
from collections.abc import Sequence


class EmployeeStatus(StrEnum):
    ACTIVE = "Đang làm"
    LEFT = "Đã nghỉ"


class UserRole(StrEnum):
    ADMIN = "Admin"
    IT_STAFF = "IT Staff"
    VIEWER = "Viewer"


@dataclass
class Employee:
    employee_id: str
    full_name: str
    department: str
    position: str
    email: str
    status: EmployeeStatus = EmployeeStatus.ACTIVE


@dataclass
class SystemAccount:
    username: str
    employee_id: str
    password_hash: str
    role: UserRole
    enabled: bool = True


class EmployeeModel:
    def __init__(self) -> None:
        self._employees: dict[str, Employee] = {}
        self._accounts: dict[str, SystemAccount] = {}

    def save_employee(self, employee: Employee) -> None:
        if not employee.employee_id.strip() or not employee.email.strip():
            raise ValueError("Mã nhân viên và email không được để trống.")
        self._employees[employee.employee_id] = employee

    def employees(self) -> Sequence[Employee]:
        return tuple(self._employees.values())

    def save_account(self, account: SystemAccount) -> None:
        if account.username in self._accounts:
            raise ValueError(f"Tài khoản '{account.username}' đã tồn tại.")
        self._accounts[account.username] = account

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from modules.employee.models import UserRole


class Permission(StrEnum):
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ADMINISTER = "administer"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset(Permission),
    UserRole.IT_STAFF: frozenset(
        {Permission.VIEW, Permission.CREATE, Permission.UPDATE}
    ),
    UserRole.VIEWER: frozenset({Permission.VIEW}),
}


@dataclass(frozen=True)
class AuditEntry:
    actor: str
    action: str
    entity: str
    entity_id: str
    occurred_at: datetime


class SystemModel:
    def __init__(self) -> None:
        self._categories: dict[str, set[str]] = {}
        self._audit_log: list[AuditEntry] = []

    def set_category_values(self, category: str, values: set[str]) -> None:
        if not category.strip() or not values or any(not value.strip() for value in values):
            raise ValueError("Danh mục và các giá trị không được để trống.")
        self._categories[category] = set(values)

    def category_values(self, category: str) -> frozenset[str]:
        return frozenset(self._categories.get(category, set()))

    def record_activity(self, entry: AuditEntry) -> None:
        self._audit_log.append(entry)

    def audit_history(self) -> tuple[AuditEntry, ...]:
        return tuple(self._audit_log)

    @staticmethod
    def has_permission(role: UserRole, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS[role]

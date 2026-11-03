from modules.system.models import AuditEntry, Permission, SystemModel
from modules.system.views import SystemView
from modules.employee.models import UserRole


class SystemController:
    def __init__(self, model: SystemModel, view: SystemView) -> None:
        self._model = model
        self._view = view

    def configure_category(self, category: str, values: set[str]) -> None:
        self._model.set_category_values(category, values)

    def record_activity(self, entry: AuditEntry) -> None:
        self._model.record_activity(entry)

    def audit_log(self) -> str:
        return self._view.render_audit_log(self._model.audit_history())

    def can(self, role: UserRole, permission: Permission) -> bool:
        return self._model.has_permission(role, permission)

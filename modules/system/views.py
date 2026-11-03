from collections.abc import Sequence

from modules.system.models import AuditEntry


class SystemView:
    @staticmethod
    def render_audit_log(entries: Sequence[AuditEntry]) -> str:
        if not entries:
            return "Chưa có nhật ký hoạt động."
        return "\n".join(
            f"{item.occurred_at.isoformat(timespec='seconds')} | {item.actor} | "
            f"{item.action} | {item.entity}:{item.entity_id}"
            for item in entries
        )

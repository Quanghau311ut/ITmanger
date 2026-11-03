from collections.abc import Sequence

from modules.maintenance.models import MaintenanceTicket


class MaintenanceView:
    @staticmethod
    def render_tickets(tickets: Sequence[MaintenanceTicket]) -> str:
        if not tickets:
            return "Chưa có phiếu bảo trì hoặc sửa chữa."
        return "\n".join(
            f"{item.ticket_id} | {item.asset_code} | {item.maintenance_type.value} | "
            f"{item.received_on} | {item.completed_on or 'Chưa hoàn thành'}"
            for item in tickets
        )

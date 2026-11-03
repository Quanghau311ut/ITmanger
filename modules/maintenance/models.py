from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum


class MaintenanceType(StrEnum):
    SCHEDULED = "Bảo trì định kỳ"
    REPAIR = "Sửa chữa đột xuất"


@dataclass
class MaintenanceTicket:
    ticket_id: str
    asset_code: str
    maintenance_type: MaintenanceType
    received_on: date
    issue_description: str
    handler: str
    cost: Decimal = Decimal("0")
    replacement_parts: list[str] = field(default_factory=list)
    completed_on: date | None = None


class MaintenanceModel:
    def __init__(self) -> None:
        self._tickets: dict[str, MaintenanceTicket] = {}

    def create_ticket(self, ticket: MaintenanceTicket) -> None:
        if ticket.ticket_id in self._tickets:
            raise ValueError(f"Mã phiếu '{ticket.ticket_id}' đã tồn tại.")
        if not ticket.cost.is_finite() or ticket.cost < 0:
            raise ValueError("Chi phí phải là số hữu hạn không âm.")
        self._tickets[ticket.ticket_id] = ticket

    def complete_ticket(self, ticket_id: str, completed_on: date) -> MaintenanceTicket:
        try:
            ticket = self._tickets[ticket_id]
        except KeyError as error:
            raise KeyError(f"Không tìm thấy phiếu bảo trì '{ticket_id}'.") from error
        ticket.completed_on = completed_on
        return ticket

    def history_for_asset(self, asset_code: str) -> tuple[MaintenanceTicket, ...]:
        return tuple(item for item in self._tickets.values() if item.asset_code == asset_code)

    def get_all(self) -> tuple[MaintenanceTicket, ...]:
        return tuple(self._tickets.values())

    @staticmethod
    def due_for_maintenance(due_dates: dict[str, date], today: date) -> tuple[str, ...]:
        return tuple(code for code, due_date in due_dates.items() if due_date <= today)

    @staticmethod
    def warranty_expiring(
        warranty_dates: dict[str, date], today: date, within_days: int = 30
    ) -> tuple[str, ...]:
        if within_days < 0:
            raise ValueError("Số ngày cảnh báo không thể âm.")
        latest_date = today + timedelta(days=within_days)
        return tuple(
            code for code, warranty_date in warranty_dates.items()
            if today <= warranty_date <= latest_date
        )

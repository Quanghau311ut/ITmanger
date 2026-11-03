from datetime import date

from modules.maintenance.models import MaintenanceModel, MaintenanceTicket
from modules.maintenance.views import MaintenanceView


class MaintenanceController:
    def __init__(self, model: MaintenanceModel, view: MaintenanceView) -> None:
        self._model = model
        self._view = view

    def create_ticket(self, ticket: MaintenanceTicket) -> None:
        self._model.create_ticket(ticket)

    def complete_ticket(self, ticket_id: str, completed_on: date) -> MaintenanceTicket:
        return self._model.complete_ticket(ticket_id, completed_on)

    def asset_history(self, asset_code: str) -> str:
        return self._view.render_tickets(self._model.history_for_asset(asset_code))

from modules.inventory.models import InventoryModel, InventoryRun
from modules.inventory.views import InventoryView


class InventoryController:
    def __init__(self, model: InventoryModel, view: InventoryView) -> None:
        self._model = model
        self._view = view

    def create_run(self, run: InventoryRun) -> None:
        self._model.create_run(run)

    def scan(self, run_id: str, asset_code: str, actual_location: str) -> None:
        self._model.get_run(run_id).scan(asset_code, actual_location)

    def report_discrepancies(self, run_id: str) -> str:
        return self._view.render_discrepancies(self._model.get_run(run_id).discrepancies())

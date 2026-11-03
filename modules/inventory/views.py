from collections.abc import Sequence

from modules.inventory.models import InventoryDiscrepancy, InventoryRun


class InventoryView:
    @staticmethod
    def render_history(runs: Sequence[InventoryRun]) -> str:
        if not runs:
            return "Chưa có đợt kiểm kê."
        return "\n".join(f"{run.run_id} | {run.scope} | {run.created_on}" for run in runs)

    @staticmethod
    def render_discrepancies(items: Sequence[InventoryDiscrepancy]) -> str:
        if not items:
            return "Không có chênh lệch kiểm kê."
        return "\n".join(
            f"{item.asset_code} | {item.discrepancy_type.value} | "
            f"{item.expected_location or '-'} -> {item.actual_location or '-'}"
            for item in items
        )

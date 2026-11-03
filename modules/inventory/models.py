from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class DiscrepancyType(StrEnum):
    MISSING = "Thiếu"
    EXTRA = "Thừa"
    WRONG_LOCATION = "Sai vị trí"


@dataclass(frozen=True)
class InventoryDiscrepancy:
    asset_code: str
    discrepancy_type: DiscrepancyType
    expected_location: str | None = None
    actual_location: str | None = None


@dataclass
class InventoryRun:
    run_id: str
    created_on: date
    scope: str
    expected_assets: dict[str, str]
    scanned_assets: dict[str, str] = field(default_factory=dict)

    def scan(self, asset_code: str, actual_location: str) -> None:
        self.scanned_assets[asset_code] = actual_location

    def discrepancies(self) -> tuple[InventoryDiscrepancy, ...]:
        results: list[InventoryDiscrepancy] = []
        for code in self.expected_assets.keys() - self.scanned_assets.keys():
            results.append(InventoryDiscrepancy(code, DiscrepancyType.MISSING, self.expected_assets[code]))
        for code in self.scanned_assets.keys() - self.expected_assets.keys():
            results.append(InventoryDiscrepancy(code, DiscrepancyType.EXTRA, actual_location=self.scanned_assets[code]))
        for code in self.expected_assets.keys() & self.scanned_assets.keys():
            expected = self.expected_assets[code]
            actual = self.scanned_assets[code]
            if expected != actual:
                results.append(
                    InventoryDiscrepancy(code, DiscrepancyType.WRONG_LOCATION, expected, actual)
                )
        return tuple(sorted(results, key=lambda item: (item.asset_code, item.discrepancy_type.value)))


class InventoryModel:
    def __init__(self) -> None:
        self._runs: dict[str, InventoryRun] = {}

    def create_run(self, run: InventoryRun) -> None:
        if run.run_id in self._runs:
            raise ValueError(f"Mã đợt kiểm kê '{run.run_id}' đã tồn tại.")
        self._runs[run.run_id] = run

    def get_run(self, run_id: str) -> InventoryRun:
        try:
            return self._runs[run_id]
        except KeyError as error:
            raise KeyError(f"Không tìm thấy đợt kiểm kê '{run_id}'.") from error

    def history(self) -> tuple[InventoryRun, ...]:
        return tuple(self._runs.values())

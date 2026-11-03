from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol


class AssetRecord(Protocol):
    category: str
    location: str
    status: StrEnum


@dataclass(frozen=True)
class AssetSummary:
    by_category: dict[str, int]
    by_status: dict[str, int]
    by_location: dict[str, int]


class ReportingModel:
    @staticmethod
    def summarize_assets(assets: tuple[AssetRecord, ...]) -> AssetSummary:
        return AssetSummary(
            by_category=dict(Counter(item.category for item in assets)),
            by_status=dict(Counter(str(item.status.value) for item in assets)),
            by_location=dict(Counter(item.location for item in assets)),
        )

    @staticmethod
    def total_repair_cost(costs: tuple[Decimal, ...]) -> Decimal:
        return sum(costs, Decimal("0"))

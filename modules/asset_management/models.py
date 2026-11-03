from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


class AssetStatus(StrEnum):
    IN_USE = "Đang dùng"
    AVAILABLE = "Sẵn sàng"
    UNDER_REPAIR = "Đang sửa"
    RETIRED = "Thanh lý"


@dataclass(frozen=True)
class AssetChange:
    changed_at: datetime
    description: str
    before: tuple[tuple[str, str], ...] = ()
    after: tuple[tuple[str, str], ...] = ()


@dataclass
class Asset:
    asset_code: str
    serial_number: str
    model: str
    manufacturer: str
    purchase_date: date
    value: Decimal
    warranty_until: date | None
    location: str
    status: AssetStatus
    category: str
    attachments: list[str] = field(default_factory=list)
    history: list[AssetChange] = field(default_factory=list)


class AssetModel:
    """In-memory asset repository with CRUD and a basic change history."""

    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}

    def create(self, asset: Asset) -> None:
        self._validate(asset)
        if asset.asset_code in self._assets:
            raise ValueError(f"Mã tài sản '{asset.asset_code}' đã tồn tại.")
        asset.history.append(
            AssetChange(datetime.now(), "Tạo mới tài sản", after=self._snapshot(asset))
        )
        self._assets[asset.asset_code] = asset

    def get(self, asset_code: str) -> Asset:
        try:
            return self._assets[asset_code]
        except KeyError as error:
            raise KeyError(f"Không tìm thấy tài sản '{asset_code}'.") from error

    def get_all(self) -> tuple[Asset, ...]:
        return tuple(self._assets.values())

    def update(self, asset_code: str, **changes: object) -> Asset:
        current = self.get(asset_code)
        if "asset_code" in changes or "history" in changes:
            raise ValueError("Không thể sửa mã tài sản hoặc lịch sử bằng thao tác cập nhật.")
        description = ", ".join(sorted(changes)) or "Không có thay đổi"
        updated = replace(current, **changes)
        self._validate(updated)
        updated.history = [
            *current.history,
            AssetChange(
                datetime.now(),
                f"Cập nhật: {description}",
                before=self._snapshot(current),
                after=self._snapshot(updated),
            ),
        ]
        self._assets[asset_code] = updated
        return updated

    def delete(self, asset_code: str) -> None:
        self.get(asset_code)
        del self._assets[asset_code]

    @staticmethod
    def _validate(asset: Asset) -> None:
        validate_asset(asset)

    @staticmethod
    def _snapshot(asset: Asset) -> tuple[tuple[str, str], ...]:
        return snapshot_asset(asset)


def validate_asset(asset: Asset) -> None:
    if not asset.asset_code.strip():
        raise ValueError("Mã tài sản không được để trống.")
    if not asset.category.strip() or not asset.location.strip():
        raise ValueError("Loại thiết bị và vị trí không được để trống.")
    if not asset.value.is_finite() or asset.value < 0:
        raise ValueError("Giá trị tài sản phải là số hữu hạn không âm.")


def snapshot_asset(asset: Asset) -> tuple[tuple[str, str], ...]:
    return tuple(
        (name, repr(value))
        for name, value in vars(asset).items()
        if name != "history"
    )

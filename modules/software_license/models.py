from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum


class LicenseType(StrEnum):
    PERPETUAL = "Vĩnh viễn"
    SUBSCRIPTION = "Thuê bao"


@dataclass
class SoftwareLicense:
    license_id: str
    software_name: str
    license_type: LicenseType
    quantity: int
    expires_on: date | None = None
    assigned_to: set[str] = field(default_factory=set)

    def assign_to(self, subject_id: str) -> None:
        if self.quantity < 1:
            raise ValueError("Số lượng license phải lớn hơn 0.")
        if subject_id not in self.assigned_to and len(self.assigned_to) >= self.quantity:
            raise ValueError("Đã sử dụng hết số lượng license.")
        self.assigned_to.add(subject_id)

    def is_expiring(self, today: date, within_days: int = 30) -> bool:
        if within_days < 0:
            raise ValueError("Số ngày cảnh báo không thể âm.")
        return self.expires_on is not None and today <= self.expires_on <= today + timedelta(days=within_days)


@dataclass(frozen=True)
class SoftwareInstallation:
    software_name: str
    asset_code: str
    installed_on: date


class SoftwareLicenseModel:
    def __init__(self) -> None:
        self._licenses: dict[str, SoftwareLicense] = {}
        self._installations: list[SoftwareInstallation] = []

    def add_license(self, license_item: SoftwareLicense) -> None:
        if license_item.license_id in self._licenses:
            raise ValueError(f"Mã license '{license_item.license_id}' đã tồn tại.")
        if license_item.quantity < 1:
            raise ValueError("Số lượng license phải lớn hơn 0.")
        self._licenses[license_item.license_id] = license_item

    def licenses(self) -> tuple[SoftwareLicense, ...]:
        return tuple(self._licenses.values())

    def record_installation(self, installation: SoftwareInstallation) -> None:
        self._installations.append(installation)

    def installations_for_asset(self, asset_code: str) -> tuple[SoftwareInstallation, ...]:
        return tuple(item for item in self._installations if item.asset_code == asset_code)

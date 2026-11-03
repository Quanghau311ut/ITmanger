from datetime import date

from modules.software_license.models import SoftwareLicense, SoftwareLicenseModel
from modules.software_license.views import SoftwareLicenseView


class SoftwareLicenseController:
    def __init__(self, model: SoftwareLicenseModel, view: SoftwareLicenseView) -> None:
        self._model = model
        self._view = view

    def expiring_soon(self, today: date) -> tuple[SoftwareLicense, ...]:
        return tuple(item for item in self._model.licenses() if item.is_expiring(today))

    def list_licenses(self) -> str:
        return self._view.render_licenses(self._model.licenses())

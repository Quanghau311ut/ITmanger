from modules.asset_management.models import Asset, AssetModel
from modules.asset_management.views import AssetView


class AssetController:
    def __init__(self, model: AssetModel, view: AssetView) -> None:
        self._model = model
        self._view = view

    def create(self, asset: Asset) -> None:
        self._model.create(asset)

    def update(self, asset_code: str, **changes: object) -> Asset:
        return self._model.update(asset_code, **changes)

    def delete(self, asset_code: str) -> None:
        self._model.delete(asset_code)

    def details(self, asset_code: str) -> Asset:
        return self._model.get(asset_code)

    def list_assets(self) -> str:
        return self._view.render_list(self._model.get_all())

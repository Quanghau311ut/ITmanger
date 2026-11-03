from modules.asset_management.models import Asset
from modules.reporting.models import ReportingModel
from modules.reporting.views import ReportingView


class ReportingController:
    def __init__(self, model: ReportingModel, view: ReportingView) -> None:
        self._model = model
        self._view = view

    def asset_summary(self, assets: tuple[Asset, ...]) -> str:
        return self._view.render_asset_summary(self._model.summarize_assets(assets))

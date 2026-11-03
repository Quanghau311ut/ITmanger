from collections.abc import Sequence

from modules.asset_management.models import Asset


class AssetView:
    @staticmethod
    def render_list(assets: Sequence[Asset]) -> str:
        if not assets:
            return "Chưa có tài sản nào."
        header = "Mã tài sản | Thiết bị | Loại | Vị trí | Tình trạng"
        rows = [
            f"{asset.asset_code} | {asset.model} | {asset.category} | "
            f"{asset.location} | {asset.status.value}"
            for asset in assets
        ]
        return "\n".join([header, *rows])

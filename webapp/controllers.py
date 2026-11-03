import re
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
from urllib.parse import parse_qs, unquote, urlencode

from modules.asset_management.models import Asset, AssetModel, AssetStatus
from modules.maintenance.models import MaintenanceModel, MaintenanceTicket, MaintenanceType
from webapp.views import MODULES, asset_page, dashboard, maintenance_page, module_placeholder


class WebController:
    def __init__(self, assets: AssetModel, maintenance: MaintenanceModel) -> None:
        self._assets = assets
        self._maintenance = maintenance

    def page(
        self, target: str, query: str = "", notice: str = "", error: str = ""
    ) -> tuple[int, str]:
        routes = {path: key for key, _, path in MODULES}
        key = routes.get(target)
        if target == "/":
            return 200, dashboard(self._assets.get_all(), self._maintenance.get_all())
        if target == "/assets":
            html = asset_page(self._assets.get_all(), query, notice)
            return (400 if error else 200), self._add_error_notice(html, error)
        if target == "/maintenance":
            html = maintenance_page(
                self._maintenance.get_all(), self._assets.get_all(), notice
            )
            return (400 if error else 200), self._add_error_notice(html, error)
        if key in {"assignment", "inventory", "software", "employees", "reports", "system"}:
            return 200, module_placeholder(key)
        return 404, self.render_error("Không tìm thấy trang được yêu cầu.")

    def submit(self, target: str, fields: dict[str, str]) -> str:
        if target == "/assets":
            asset = self._asset_from_form(fields)
            self._assets.create(asset)
            return self._redirect("/assets", "Đã thêm tài sản.")
        if target == "/maintenance":
            ticket = self._ticket_from_form(fields)
            self._assets.get(ticket.asset_code)
            self._maintenance.create_ticket(ticket)
            return self._redirect("/maintenance", "Đã tạo phiếu bảo trì.")
        match = re.fullmatch(r"/maintenance/([^/]+)/complete", target)
        if match:
            ticket_id = unquote(match.group(1))
            self._maintenance.complete_ticket(ticket_id, date.today())
            return self._redirect("/maintenance", "Đã cập nhật phiếu hoàn thành.")
        raise ValueError("Thao tác không hợp lệ.")

    @staticmethod
    def _asset_from_form(fields: dict[str, str]) -> Asset:
        try:
            purchase_date = date.fromisoformat(fields.get("purchase_date", "").strip()) \
                if fields.get("purchase_date", "").strip() else date.today()
            warranty_value = fields.get("warranty_until", "").strip()
            warranty_until = date.fromisoformat(warranty_value) if warranty_value else None
            value = Decimal(fields.get("value", "0").strip() or "0")
            if not value.is_finite() or value < 0:
                raise ValueError("Giá trị tài sản phải là số không âm.")
            status_by_label = {status.value: status for status in AssetStatus}
            status = status_by_label[fields.get("status", AssetStatus.AVAILABLE.value)]
            asset = Asset(
                asset_code=fields.get("asset_code", "").strip(),
                serial_number=fields.get("serial_number", "").strip(),
                model=fields.get("model", "").strip(),
                manufacturer=fields.get("manufacturer", "").strip(),
                purchase_date=purchase_date,
                value=value,
                warranty_until=warranty_until,
                location=fields.get("location", "").strip(),
                status=status,
                category=fields.get("category", "").strip(),
            )
        except (InvalidOperation, ValueError, KeyError) as error:
            raise ValueError("Thông tin tài sản không hợp lệ. Vui lòng kiểm tra các trường đã nhập.") from error
        if not asset.model.strip():
            raise ValueError("Tên model không được để trống.")
        return asset

    @staticmethod
    def _ticket_from_form(fields: dict[str, str]) -> MaintenanceTicket:
        try:
            type_by_key = {
                "scheduled": MaintenanceType.SCHEDULED,
                "repair": MaintenanceType.REPAIR,
            }
            cost = Decimal(fields.get("cost", "0").strip() or "0")
            if not cost.is_finite() or cost < 0:
                raise ValueError("Chi phí phải là số không âm.")
            ticket = MaintenanceTicket(
                ticket_id=fields.get("ticket_id", "").strip(),
                asset_code=fields.get("asset_code", "").strip(),
                maintenance_type=type_by_key[fields.get("maintenance_type", "repair")],
                received_on=date.fromisoformat(fields.get("received_on", "").strip()),
                issue_description=fields.get("issue_description", "").strip(),
                handler=fields.get("handler", "").strip(),
                cost=cost,
                replacement_parts=[
                    part.strip() for part in fields.get("replacement_parts", "").split(",")
                    if part.strip()
                ],
            )
        except (InvalidOperation, ValueError, KeyError) as error:
            raise ValueError("Thông tin phiếu không hợp lệ. Vui lòng kiểm tra các trường đã nhập.") from error
        if not ticket.ticket_id or not ticket.issue_description or not ticket.handler:
            raise ValueError("Mã phiếu, mô tả và người xử lý không được để trống.")
        return ticket

    @staticmethod
    def _redirect(path: str, message: str) -> str:
        return f"{path}?{urlencode({'notice': message})}"

    @staticmethod
    def render_error(message: str) -> str:
        from webapp.views import _shell

        content = (
            '<div class="page-heading"><div><div class="eyebrow">REQUEST ERROR</div>'
            '<h1>Không thể xử lý yêu cầu</h1></div></div>'
            f'<section class="panel"><p>{escape(message)}</p>'
            '<a class="button secondary" href="/">Về tổng quan</a></section>'
        )
        return _shell("Lỗi", content, "dashboard")

    @staticmethod
    def _add_error_notice(html: str, message: str) -> str:
        if not message:
            return html
        notice = f'<div class="notice error">{escape(message)}</div>'
        return html.replace('<section class="page">', f'<section class="page">{notice}', 1)


def parse_form(body: bytes) -> dict[str, str]:
    try:
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True, strict_parsing=True)
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("Dữ liệu biểu mẫu không hợp lệ.") from error
    return {key: values[-1] for key, values in parsed.items()}

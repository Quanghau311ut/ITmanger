import re
import csv
from io import StringIO
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Protocol
from urllib.parse import parse_qs, unquote, urlencode

from modules.asset_management.models import Asset, AssetStatus
from modules.maintenance.models import MaintenanceTicket, MaintenanceType
from webapp.views import MODULES, asset_page, dashboard, maintenance_page, module_placeholder, workflow_page


class AssetRepository(Protocol):
    def create(self, asset: Asset) -> None: ...

    def get(self, asset_code: str) -> Asset: ...

    def get_all(self) -> tuple[Asset, ...]: ...

    def update(self, asset_code: str, **changes: object) -> Asset: ...


class MaintenanceRepository(Protocol):
    def create_ticket(self, ticket: MaintenanceTicket) -> None: ...

    def complete_ticket(self, ticket_id: str, completed_on: date) -> MaintenanceTicket: ...

    def get_all(self) -> tuple[MaintenanceTicket, ...]: ...


class WebController:
    def __init__(
        self,
        assets: AssetRepository,
        maintenance: MaintenanceRepository,
        modules=None,
    ) -> None:
        self._assets = assets
        self._maintenance = maintenance
        self._modules = modules

    def page(
        self, target: str, query: str = "", notice: str = "", error: str = ""
    ) -> tuple[int, str]:
        # Treat a trailing slash as the same page so copied/bookmarked URLs
        # resolve to the same module as the sidebar's canonical links.
        target = target.rstrip("/") or "/"
        routes = {path: key for key, _, path in MODULES}
        key = routes.get(target)
        if target == "/":
            return 200, dashboard(self._assets.get_all(), self._maintenance.get_all())
        if target == "/assets":
            configured = {
                item["category"]: item["values"] for item in self._modules.categories()
            } if self._modules is not None else {}
            html = asset_page(
                self._assets.get_all(),
                query,
                notice,
                configured.get("Loại thiết bị", ()),
                configured.get("Vị trí", ()),
            )
            return (400 if error else 200), self._add_error_notice(html, error)
        if target == "/maintenance":
            html = maintenance_page(
                self._maintenance.get_all(),
                self._assets.get_all(),
                notice,
                self._modules.maintenance_schedules() if self._modules is not None else (),
            )
            return (400 if error else 200), self._add_error_notice(html, error)
        if key in {"assignment", "inventory", "software", "employees", "reports", "system"}:
            if self._modules is None:
                return 200, module_placeholder(key)
            data = self._module_data(key)
            return 200, workflow_page(key, data, notice)
        if target == "/assignments/print" and self._modules is not None:
            assignments = self._modules.assignments()
            table = "".join(
                f'<tr><td>{escape(str(item["assignment_id"]))}</td><td>{escape(str(item["asset_code"]))}</td>'
                f'<td>{escape(str(item["employee_name"]))}</td><td>{escape(str(item["issued_on"]))}</td>'
                f'<td>{escape(str(item["return_condition"] or ""))}</td></tr>'
                for item in assignments
            )
            from webapp.views import _shell

            return 200, _shell(
                "Biên bản bàn giao / thu hồi",
                '<div class="page-heading"><h1>Biên bản bàn giao / thu hồi</h1>'
                '<span class="muted">Dùng Ctrl+P để in hoặc lưu PDF</span></div>'
                '<section class="panel"><table><thead><tr><th>Mã phiếu</th><th>Tài sản</th>'
                f'<th>Người nhận</th><th>Ngày cấp</th><th>Tình trạng thu hồi</th></tr></thead><tbody>{table}</tbody></table></section>',
                "assignment",
            )
        return 404, self.render_error("Không tìm thấy trang được yêu cầu.")

    def submit(self, target: str, fields: dict[str, str]) -> str:
        if target == "/assets":
            asset = self._asset_from_form(fields)
            asset.attachments = [
                value.strip() for value in fields.get("attachments", "").splitlines()
                if value.strip()
            ]
            self._assets.create(asset)
            self._record("Tạo", "Tài sản", asset.asset_code)
            return self._redirect("/assets", "Đã thêm tài sản.")
        match = re.fullmatch(r"/assets/([^/]+)/update", target)
        if match:
            asset_code = unquote(match.group(1))
            asset = self._asset_from_form({**fields, "asset_code": asset_code})
            asset.attachments = [
                value.strip() for value in fields.get("attachments", "").splitlines()
                if value.strip()
            ]
            self._assets.update(asset_code, **{
                "serial_number": asset.serial_number,
                "model": asset.model,
                "manufacturer": asset.manufacturer,
                "purchase_date": asset.purchase_date,
                "value": asset.value,
                "warranty_until": asset.warranty_until,
                "location": asset.location,
                "status": asset.status,
                "category": asset.category,
                "attachments": asset.attachments,
            })
            self._record("Cập nhật", "Tài sản", asset_code)
            return self._redirect("/assets", "Đã cập nhật tài sản.")
        match = re.fullmatch(r"/assets/([^/]+)/retire", target)
        if match:
            asset_code = unquote(match.group(1))
            self._assets.update(asset_code, status=AssetStatus.RETIRED)
            self._record("Thanh lý", "Tài sản", asset_code)
            return self._redirect("/assets", "Đã chuyển tài sản sang trạng thái thanh lý.")
        if target == "/maintenance":
            ticket = self._ticket_from_form(fields)
            self._assets.get(ticket.asset_code)
            self._maintenance.create_ticket(ticket)
            self._record("Tạo", "Phiếu bảo trì", ticket.ticket_id)
            return self._redirect("/maintenance", "Đã tạo phiếu bảo trì.")
        if target == "/maintenance/schedule" and self._modules is not None:
            self._modules.save_maintenance_schedule(
                fields.get("asset_code", ""),
                date.fromisoformat(fields.get("due_on", "")),
                int(fields.get("interval_days", "0")),
                fields.get("notes", ""),
            )
            self._record("Lập lịch", "Bảo trì", fields.get("asset_code", ""))
            return self._redirect("/maintenance", "Đã lưu lịch bảo trì.")
        match = re.fullmatch(r"/maintenance/([^/]+)/complete", target)
        if match:
            ticket_id = unquote(match.group(1))
            self._maintenance.complete_ticket(ticket_id, date.today())
            self._record("Hoàn thành", "Phiếu bảo trì", ticket_id)
            return self._redirect("/maintenance", "Đã cập nhật phiếu hoàn thành.")
        if self._modules is not None:
            if target == "/employees":
                self._modules.save_employee(fields)
                self._record("Lưu", "Nhân viên", fields.get("employee_id", ""))
                return self._redirect("/employees", "Đã lưu thông tin nhân viên.")
            if target == "/assignment":
                self._modules.create_assignment(
                    fields.get("assignment_id", "").strip(),
                    fields.get("asset_code", "").strip(),
                    fields.get("employee_id", "").strip(),
                    date.fromisoformat(fields.get("issued_on", "").strip()),
                    _optional_date(fields.get("due_on", "")),
                )
                self._record("Cấp phát", "Phiếu cấp phát", fields.get("assignment_id", ""))
                return self._redirect("/assignment", "Đã cấp phát thiết bị.")
            match = re.fullmatch(r"/assignment/([^/]+)/return", target)
            if match:
                assignment_id = unquote(match.group(1))
                self._modules.return_assignment(
                    assignment_id,
                    date.fromisoformat(fields.get("returned_on", date.today().isoformat())),
                    fields.get("condition", ""),
                )
                self._record("Thu hồi", "Phiếu cấp phát", assignment_id)
                return self._redirect("/assignment", "Đã ghi nhận thu hồi thiết bị.")
            if target == "/inventory":
                self._modules.create_inventory_run(
                    fields.get("run_id", "").strip(),
                    date.fromisoformat(fields.get("created_on", date.today().isoformat())),
                    fields.get("scope_type", ""),
                    fields.get("scope_value", "").strip(),
                )
                self._record("Tạo", "Đợt kiểm kê", fields.get("run_id", ""))
                return self._redirect("/inventory", "Đã tạo đợt kiểm kê.")
            match = re.fullmatch(r"/inventory/([^/]+)/scan", target)
            if match:
                run_id = unquote(match.group(1))
                self._modules.scan_inventory(
                    run_id, fields.get("asset_code", ""), fields.get("actual_location", "")
                )
                self._record("Quét", "Đợt kiểm kê", run_id)
                return self._redirect("/inventory", "Đã ghi nhận tài sản kiểm kê.")
            if target == "/software/license":
                quantity = int(fields.get("quantity", "0"))
                self._modules.save_license(
                    fields.get("license_id", ""),
                    fields.get("software_name", ""),
                    fields.get("license_type", ""),
                    quantity,
                    _optional_date(fields.get("expires_on", "")),
                )
                self._record("Lưu", "License", fields.get("license_id", ""))
                return self._redirect("/software", "Đã lưu license.")
            if target == "/software/assign":
                license_id = fields.get("license_id", "")
                self._modules.assign_license(license_id, fields.get("subject_id", ""))
                self._record("Gán", "License", license_id)
                return self._redirect("/software", "Đã gán license.")
            if target == "/software/unassign":
                license_id = fields.get("license_id", "")
                subject_id = fields.get("subject_id", "")
                self._modules.unassign_license(license_id, subject_id)
                self._record("Thu hồi", "License", f"{license_id}: {subject_id}")
                return self._redirect("/software", "Đã thu hồi license.")
            if target == "/software/install":
                self._modules.install_software(
                    fields.get("software_name", ""),
                    fields.get("asset_code", ""),
                    date.fromisoformat(fields.get("installed_on", date.today().isoformat())),
                )
                self._record("Cài đặt", "Phần mềm", fields.get("asset_code", ""))
                return self._redirect("/software", "Đã ghi nhận phần mềm cài đặt.")
            if target == "/system/categories":
                self._modules.save_category(
                    fields.get("category", ""), fields.get("values", "").split(",")
                )
                self._record("Cập nhật", "Danh mục", fields.get("category", ""))
                return self._redirect("/system", "Đã cập nhật danh mục.")
            if target == "/system/accounts":
                self._modules.save_account(
                    fields.get("username", ""),
                    fields.get("employee_id", ""),
                    fields.get("password", ""),
                    fields.get("role", ""),
                )
                self._record("Tạo", "Tài khoản", fields.get("username", ""))
                return self._redirect("/system", "Đã tạo tài khoản.")
            if target == "/system/accounts/access":
                username = fields.get("username", "")
                role = fields.get("role", "")
                enabled = fields.get("enabled", "") == "true"
                self._modules.update_account_access(username, role, enabled)
                self._record("Cập nhật quyền", "Tài khoản", username)
                return self._redirect("/system", "Đã cập nhật vai trò/trạng thái tài khoản.")
            if target == "/system/password":
                session_user = fields.get("_session_username", "")
                if not session_user:
                    raise ValueError("Phiên đăng nhập không hợp lệ.")
                self._modules.change_password(
                    session_user,
                    fields.get("current_password", ""),
                    fields.get("new_password", ""),
                )
                self._record("Đổi mật khẩu", "Tài khoản", session_user)
                return self._redirect("/system", "Đã đổi mật khẩu.")
        raise ValueError("Thao tác không hợp lệ.")

    def export(self, target: str) -> tuple[str, str]:
        if self._modules is None:
            raise ValueError("Báo cáo yêu cầu kết nối cơ sở dữ liệu.")
        inventory_match = re.fullmatch(r"/inventory/export/([^/]+)\.csv", target)
        if inventory_match:
            run_id = unquote(inventory_match.group(1))
            run = next(
                (item for item in self._modules.inventory_runs() if item["run_id"] == run_id),
                None,
            )
            if run is None:
                raise ValueError("Không tìm thấy đợt kiểm kê.")
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(("Mã tài sản", "Chênh lệch", "Vị trí hệ thống", "Vị trí thực tế"))
            writer.writerows(
                tuple(
                    _spreadsheet_safe(value)
                    for value in (
                    item["asset_code"],
                    item["type"],
                    item["expected"],
                    item["actual"],
                    )
                )
                for item in run["discrepancies"]
            )
            safe_run_id = re.sub(r"[^A-Za-z0-9_-]", "_", run_id)
            return f"inventory_{safe_run_id}.csv", "\ufeff" + output.getvalue()
        data = self._modules.report_data()
        if target == "/reports/export/assets.csv":
            headers = ("Mã tài sản", "Loại", "Tình trạng", "Vị trí", "Giá trị", "Bảo hành đến")
            rows = (
                (
                    row["asset_code"], row["category"], row["status"], row["location"],
                    row["value"], row["warranty_until"] or "",
                )
                for row in data["assets"]
            )
            filename = "assets.csv"
        elif target == "/reports/export/maintenance.csv":
            headers = ("Mã phiếu", "Mã tài sản", "Ngày tiếp nhận", "Chi phí")
            rows = (
                (row["ticket_id"], row["asset_code"], row["received_on"], row["cost"])
                for row in data["maintenance"]
            )
            filename = "maintenance.csv"
        elif target == "/reports/export/licenses.csv":
            headers = ("Mã license", "Phần mềm", "Ngày hết hạn", "Số lượng")
            rows = (
                (row["license_id"], row["software_name"], row["expires_on"] or "", row["quantity"])
                for row in data["licenses"]
            )
            filename = "licenses.csv"
        else:
            raise ValueError("Không tìm thấy báo cáo.")
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(tuple(_spreadsheet_safe(value) for value in row) for row in rows)
        return filename, "\ufeff" + output.getvalue()

    def _module_data(self, key: str) -> dict[str, object]:
        if key == "assignment":
            return {
                "assets": self._assets.get_all(),
                "employees": self._modules.employees(),
                "assignments": self._modules.assignments(),
            }
        if key == "inventory":
            return {"assets": self._assets.get_all(), "runs": self._modules.inventory_runs()}
        if key == "software":
            return {
                "assets": self._assets.get_all(),
                "employees": self._modules.employees(),
                "licenses": self._modules.licenses(),
                "installations": self._modules.installations(),
            }
        if key == "employees":
            return {"employees": self._modules.employees()}
        if key == "system":
            return {
                "categories": self._modules.categories(),
                "audit": self._modules.audit_logs(),
                "accounts": self._modules.accounts(),
                "employees": self._modules.employees(),
            }
        return self._modules.report_data()

    def _record(self, action: str, entity: str, entity_id: str) -> None:
        if self._modules is not None:
            self._modules.record_activity(action, entity, entity_id)

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


def _optional_date(value: str) -> date | None:
    value = value.strip()
    return date.fromisoformat(value) if value else None


def _spreadsheet_safe(value: object) -> object:
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value

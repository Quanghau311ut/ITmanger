import json
import hashlib
import hmac
import secrets
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, Unicode, UnicodeText, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship, sessionmaker

from modules.asset_management.models import (
    Asset,
    AssetChange,
    AssetStatus,
    snapshot_asset,
    validate_asset,
)
from modules.database import Base, Database
from modules.maintenance.models import MaintenanceTicket, MaintenanceType


class AssetRow(Base):
    __tablename__ = "assets"

    asset_code: Mapped[str] = mapped_column(Unicode(100), primary_key=True)
    serial_number: Mapped[str] = mapped_column(Unicode(255), default="")
    model: Mapped[str] = mapped_column(Unicode(255))
    manufacturer: Mapped[str] = mapped_column(Unicode(255), default="")
    purchase_date: Mapped[date] = mapped_column(Date)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    warranty_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str] = mapped_column(Unicode(255))
    status: Mapped[str] = mapped_column(Unicode(50))
    category: Mapped[str] = mapped_column(Unicode(100))
    changes: Mapped[list["AssetChangeRow"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", order_by="AssetChangeRow.id"
    )
    attachments: Mapped[list["AssetAttachmentRow"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )


class AssetChangeRow(Base):
    __tablename__ = "asset_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_code: Mapped[str] = mapped_column(
        ForeignKey("assets.asset_code", ondelete="CASCADE"), index=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime)
    description: Mapped[str] = mapped_column(Unicode(500))
    before_json: Mapped[str] = mapped_column(UnicodeText, default="[]")
    after_json: Mapped[str] = mapped_column(UnicodeText, default="[]")
    asset: Mapped[AssetRow] = relationship(back_populates="changes")


class AssetAttachmentRow(Base):
    __tablename__ = "asset_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_code: Mapped[str] = mapped_column(
        ForeignKey("assets.asset_code", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(Unicode(1024))
    asset: Mapped[AssetRow] = relationship(back_populates="attachments")


class MaintenanceTicketRow(Base):
    __tablename__ = "maintenance_tickets"

    ticket_id: Mapped[str] = mapped_column(Unicode(100), primary_key=True)
    asset_code: Mapped[str] = mapped_column(
        ForeignKey("assets.asset_code"), index=True
    )
    maintenance_type: Mapped[str] = mapped_column(Unicode(100))
    received_on: Mapped[date] = mapped_column(Date)
    issue_description: Mapped[str] = mapped_column(UnicodeText)
    handler: Mapped[str] = mapped_column(Unicode(255))
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    completed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    parts: Mapped[list["MaintenancePartRow"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="MaintenancePartRow.id"
    )


class MaintenancePartRow(Base):
    __tablename__ = "maintenance_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(
        ForeignKey("maintenance_tickets.ticket_id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Unicode(255))
    ticket: Mapped[MaintenanceTicketRow] = relationship(back_populates="parts")


class MaintenanceScheduleRow(Base):
    __tablename__ = "maintenance_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_code: Mapped[str] = mapped_column(
        ForeignKey("assets.asset_code"), index=True
    )
    due_on: Mapped[date] = mapped_column(Date)
    interval_days: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(UnicodeText)


class EmployeeRow(Base):
    __tablename__ = "employees"

    employee_id: Mapped[str] = mapped_column(Unicode(100), primary_key=True)
    full_name: Mapped[str] = mapped_column(Unicode(255))
    department: Mapped[str] = mapped_column(Unicode(255))
    position: Mapped[str] = mapped_column(Unicode(255))
    email: Mapped[str] = mapped_column(Unicode(320), unique=True)
    status: Mapped[str] = mapped_column(Unicode(50))


class SystemAccountRow(Base):
    __tablename__ = "system_accounts"

    username: Mapped[str] = mapped_column(Unicode(100), primary_key=True)
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id"), unique=True
    )
    password_hash: Mapped[str] = mapped_column(Unicode(512))
    role: Mapped[str] = mapped_column(Unicode(50))
    enabled: Mapped[bool] = mapped_column(default=True)


class AssignmentRow(Base):
    __tablename__ = "assignments"

    assignment_id: Mapped[str] = mapped_column(Unicode(100), primary_key=True)
    asset_code: Mapped[str] = mapped_column(
        ForeignKey("assets.asset_code"), index=True
    )
    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.employee_id"), index=True
    )
    issued_on: Mapped[date] = mapped_column(Date)
    due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    returned_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    return_condition: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    status: Mapped[str] = mapped_column(Unicode(50))


class InventoryRunRow(Base):
    __tablename__ = "inventory_runs"

    run_id: Mapped[str] = mapped_column(Unicode(100), primary_key=True)
    created_on: Mapped[date] = mapped_column(Date)
    scope: Mapped[str] = mapped_column(Unicode(255))
    scans: Mapped[list["InventoryScanRow"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    expected_assets: Mapped[list["InventoryExpectedRow"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class InventoryExpectedRow(Base):
    __tablename__ = "inventory_expected_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("inventory_runs.run_id", ondelete="CASCADE"), index=True
    )
    asset_code: Mapped[str] = mapped_column(Unicode(100), index=True)
    expected_location: Mapped[str] = mapped_column(Unicode(255))
    run: Mapped[InventoryRunRow] = relationship(back_populates="expected_assets")


class InventoryScanRow(Base):
    __tablename__ = "inventory_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("inventory_runs.run_id", ondelete="CASCADE"), index=True
    )
    asset_code: Mapped[str] = mapped_column(Unicode(100), index=True)
    actual_location: Mapped[str] = mapped_column(Unicode(255))
    run: Mapped[InventoryRunRow] = relationship(back_populates="scans")


class SoftwareLicenseRow(Base):
    __tablename__ = "software_licenses"

    license_id: Mapped[str] = mapped_column(Unicode(100), primary_key=True)
    software_name: Mapped[str] = mapped_column(Unicode(255))
    license_type: Mapped[str] = mapped_column(Unicode(100))
    quantity: Mapped[int] = mapped_column(Integer)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class LicenseAssignmentRow(Base):
    __tablename__ = "license_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    license_id: Mapped[str] = mapped_column(
        ForeignKey("software_licenses.license_id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[str] = mapped_column(Unicode(100), index=True)


class SoftwareInstallationRow(Base):
    __tablename__ = "software_installations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    software_name: Mapped[str] = mapped_column(Unicode(255))
    asset_code: Mapped[str] = mapped_column(
        ForeignKey("assets.asset_code", ondelete="CASCADE"), index=True
    )
    installed_on: Mapped[date] = mapped_column(Date)


class AuditLogRow(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(Unicode(255))
    action: Mapped[str] = mapped_column(Unicode(100))
    entity: Mapped[str] = mapped_column(Unicode(100))
    entity_id: Mapped[str] = mapped_column(Unicode(255))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class SystemCategoryRow(Base):
    __tablename__ = "system_categories"

    category: Mapped[str] = mapped_column(Unicode(100), primary_key=True)
    values_json: Mapped[str] = mapped_column(UnicodeText)


class SQLAssetModel:
    def __init__(self, database: Database) -> None:
        if database.sessions is None:
            raise RuntimeError("Initialize the database before creating repositories.")
        self._sessions: sessionmaker[Session] = database.sessions

    def create(self, asset: Asset) -> None:
        validate_asset(asset)
        with self._sessions.begin() as session:
            if session.get(AssetRow, asset.asset_code) is not None:
                raise ValueError(f"Mã tài sản '{asset.asset_code}' đã tồn tại.")
            if not asset.history:
                asset.history.append(
                    AssetChange(datetime.now(), "Tạo mới tài sản", after=snapshot_asset(asset))
                )
            session.add(self._to_row(asset))

    def get(self, asset_code: str) -> Asset:
        with self._sessions() as session:
            row = session.get(AssetRow, asset_code)
            if row is None:
                raise KeyError(f"Không tìm thấy tài sản '{asset_code}'.")
            return self._to_domain(row)

    def get_all(self) -> tuple[Asset, ...]:
        with self._sessions() as session:
            rows = session.scalars(select(AssetRow).order_by(AssetRow.asset_code)).all()
            return tuple(self._to_domain(row) for row in rows)

    def update(self, asset_code: str, **changes: object) -> Asset:
        from dataclasses import replace
        if "asset_code" in changes or "history" in changes:
            raise ValueError("Không thể sửa mã tài sản hoặc lịch sử bằng thao tác cập nhật.")
        with self._sessions.begin() as session:
            row = session.get(AssetRow, asset_code)
            if row is None:
                raise KeyError(f"Không tìm thấy tài sản '{asset_code}'.")
            current = self._to_domain(row)
            updated = replace(current, **changes)
            validate_asset(updated)
            active_assignment = session.scalar(
                select(AssignmentRow).where(
                    AssignmentRow.asset_code == asset_code,
                    AssignmentRow.status == "Đang cấp phát",
                )
            )
            if active_assignment is not None and updated.status != AssetStatus.IN_USE:
                raise ValueError("Không thể đổi trạng thái tài sản đang được cấp phát.")
            updated.history.append(
                AssetChange(
                    datetime.now(),
                    f"Cập nhật: {', '.join(sorted(changes)) or 'Không có thay đổi'}",
                    before=snapshot_asset(current),
                    after=snapshot_asset(updated),
                )
            )
            self._copy_to_row(updated, row)
            return updated

    def delete(self, asset_code: str) -> None:
        with self._sessions.begin() as session:
            row = session.get(AssetRow, asset_code)
            if row is None:
                raise KeyError(f"Không tìm thấy tài sản '{asset_code}'.")
            session.delete(row)

    @staticmethod
    def _to_row(asset: Asset) -> AssetRow:
        row = AssetRow()
        SQLAssetModel._copy_to_row(asset, row)
        return row

    @staticmethod
    def _copy_to_row(asset: Asset, row: AssetRow) -> None:
        row.asset_code = asset.asset_code
        row.serial_number = asset.serial_number
        row.model = asset.model
        row.manufacturer = asset.manufacturer
        row.purchase_date = asset.purchase_date
        row.value = asset.value
        row.warranty_until = asset.warranty_until
        row.location = asset.location
        row.status = asset.status.value
        row.category = asset.category
        attachments: list[AssetAttachmentRow] = []
        for path in asset.attachments:
            attachment = AssetAttachmentRow()
            attachment.path = path
            attachments.append(attachment)
        row.attachments = attachments
        row.changes = [SQLAssetModel._change_to_row(change) for change in asset.history]

    @staticmethod
    def _change_to_row(change: AssetChange) -> AssetChangeRow:
        row = AssetChangeRow()
        row.changed_at = change.changed_at
        row.description = change.description
        row.before_json = json.dumps(change.before, ensure_ascii=False)
        row.after_json = json.dumps(change.after, ensure_ascii=False)
        return row

    @staticmethod
    def _to_domain(row: AssetRow) -> Asset:
        changes = [
            AssetChange(
                changed_at=change.changed_at,
                description=change.description,
                before=_snapshot_from_json(change.before_json),
                after=_snapshot_from_json(change.after_json),
            )
            for change in row.changes
        ]
        return Asset(
            asset_code=row.asset_code,
            serial_number=row.serial_number,
            model=row.model,
            manufacturer=row.manufacturer,
            purchase_date=row.purchase_date,
            value=Decimal(row.value),
            warranty_until=row.warranty_until,
            location=row.location,
            status=AssetStatus(row.status),
            category=row.category,
            attachments=[item.path for item in row.attachments],
            history=changes,
        )


class SQLMaintenanceModel:
    def __init__(self, database: Database) -> None:
        if database.sessions is None:
            raise RuntimeError("Initialize the database before creating repositories.")
        self._sessions: sessionmaker[Session] = database.sessions

    def create_ticket(self, ticket: MaintenanceTicket) -> None:
        if not ticket.cost.is_finite() or ticket.cost < 0:
            raise ValueError("Chi phí phải là số hữu hạn không âm.")
        with self._sessions.begin() as session:
            if session.get(MaintenanceTicketRow, ticket.ticket_id) is not None:
                raise ValueError(f"Mã phiếu '{ticket.ticket_id}' đã tồn tại.")
            session.add(self._to_row(ticket))

    def complete_ticket(self, ticket_id: str, completed_on: date) -> MaintenanceTicket:
        with self._sessions.begin() as session:
            row = session.get(MaintenanceTicketRow, ticket_id)
            if row is None:
                raise KeyError(f"Không tìm thấy phiếu bảo trì '{ticket_id}'.")
            row.completed_on = completed_on
            return self._to_domain(row)

    def history_for_asset(self, asset_code: str) -> tuple[MaintenanceTicket, ...]:
        with self._sessions() as session:
            rows = session.scalars(
                select(MaintenanceTicketRow)
                .where(MaintenanceTicketRow.asset_code == asset_code)
                .order_by(MaintenanceTicketRow.received_on)
            ).all()
            return tuple(self._to_domain(row) for row in rows)

    def get_all(self) -> tuple[MaintenanceTicket, ...]:
        with self._sessions() as session:
            rows = session.scalars(
                select(MaintenanceTicketRow).order_by(MaintenanceTicketRow.received_on.desc())
            ).all()
            return tuple(self._to_domain(row) for row in rows)

    @staticmethod
    def _to_row(ticket: MaintenanceTicket) -> MaintenanceTicketRow:
        row = MaintenanceTicketRow()
        row.ticket_id = ticket.ticket_id
        row.asset_code = ticket.asset_code
        row.maintenance_type = ticket.maintenance_type.value
        row.received_on = ticket.received_on
        row.issue_description = ticket.issue_description
        row.handler = ticket.handler
        row.cost = ticket.cost
        row.completed_on = ticket.completed_on
        parts: list[MaintenancePartRow] = []
        for part in ticket.replacement_parts:
            replacement_part = MaintenancePartRow()
            replacement_part.name = part
            parts.append(replacement_part)
        row.parts = parts
        return row

    @staticmethod
    def _to_domain(row: MaintenanceTicketRow) -> MaintenanceTicket:
        return MaintenanceTicket(
            ticket_id=row.ticket_id,
            asset_code=row.asset_code,
            maintenance_type=MaintenanceType(row.maintenance_type),
            received_on=row.received_on,
            issue_description=row.issue_description,
            handler=row.handler,
            cost=Decimal(row.cost),
            replacement_parts=[part.name for part in row.parts],
            completed_on=row.completed_on,
        )


class SQLModuleModel:
    """Persistence operations for employee, assignment, inventory and license workflows."""

    def __init__(self, database: Database) -> None:
        if database.sessions is None:
            raise RuntimeError("Initialize the database before creating repositories.")
        self._sessions: sessionmaker[Session] = database.sessions

    def account_count(self) -> int:
        with self._sessions() as session:
            return len(session.scalars(select(SystemAccountRow)).all())

    def bootstrap_admin(
        self, username: str, password: str, employee_id: str, full_name: str, email: str
    ) -> None:
        self._validate_password(username, password)
        if not employee_id.strip() or not full_name.strip() or not email.strip():
            raise ValueError("Mã nhân viên, họ tên và email là bắt buộc.")
        with self._sessions.begin() as session:
            if session.scalar(select(SystemAccountRow)) is not None:
                raise ValueError("Tài khoản quản trị ban đầu đã được tạo.")
            if session.get(EmployeeRow, employee_id.strip()) is not None:
                raise ValueError("Mã nhân viên đã tồn tại.")
            employee = EmployeeRow()
            employee.employee_id = employee_id.strip()
            employee.full_name = full_name.strip()
            employee.department = "IT"
            employee.position = "Quản trị hệ thống"
            employee.email = email.strip()
            employee.status = "Đang làm"
            session.add(employee)
            session.flush()
            account = SystemAccountRow()
            account.username = username.strip()
            account.employee_id = employee.employee_id
            account.password_hash = _hash_password(password)
            account.role = "Admin"
            account.enabled = True
            session.add(account)

    def authenticate(self, username: str, password: str) -> str | None:
        with self._sessions() as session:
            row = session.get(SystemAccountRow, username.strip())
            if row is None or not row.enabled:
                return None
            employee = session.get(EmployeeRow, row.employee_id)
            if employee is None or employee.status != "Đang làm":
                return None
            if not _verify_password(password, row.password_hash):
                return None
            return row.role

    def account_role(self, username: str) -> str | None:
        with self._sessions() as session:
            row = session.get(SystemAccountRow, username)
            if row is None or not row.enabled:
                return None
            employee = session.get(EmployeeRow, row.employee_id)
            if employee is None or employee.status != "Đang làm":
                return None
            return row.role

    def accounts(self) -> tuple[dict[str, str], ...]:
        with self._sessions() as session:
            return tuple(
                {
                    "username": row.username,
                    "employee_id": row.employee_id,
                    "role": row.role,
                    "enabled": "Đang hoạt động" if row.enabled else "Đã khóa",
                }
                for row in session.scalars(
                    select(SystemAccountRow).order_by(SystemAccountRow.username)
                )
            )

    def save_account(
        self, username: str, employee_id: str, password: str, role: str
    ) -> None:
        self._validate_password(username, password)
        if role not in {"Admin", "IT Staff", "Viewer"}:
            raise ValueError("Vai trò tài khoản không hợp lệ.")
        with self._sessions.begin() as session:
            if session.get(SystemAccountRow, username.strip()) is not None:
                raise ValueError("Tên đăng nhập đã tồn tại.")
            employee = session.get(EmployeeRow, employee_id.strip())
            if employee is None or employee.status != "Đang làm":
                raise ValueError("Tài khoản phải gắn với nhân viên đang làm.")
            account = SystemAccountRow()
            account.username = username.strip()
            account.employee_id = employee_id.strip()
            account.password_hash = _hash_password(password)
            account.role = role
            account.enabled = True
            session.add(account)

    def update_account_access(self, username: str, role: str, enabled: bool) -> None:
        if role not in {"Admin", "IT Staff", "Viewer"}:
            raise ValueError("Vai trò tài khoản không hợp lệ.")
        with self._sessions.begin() as session:
            account = session.get(SystemAccountRow, username)
            if account is None:
                raise KeyError(f"Không tìm thấy tài khoản '{username}'.")
            if account.role == "Admin" and account.enabled and (
                role != "Admin" or not enabled
            ):
                other_admins = session.scalars(
                    select(SystemAccountRow).where(
                        SystemAccountRow.role == "Admin",
                        SystemAccountRow.enabled.is_(True),
                        SystemAccountRow.username != username,
                    )
                ).all()
                if not other_admins:
                    raise ValueError("Không thể khóa hoặc hạ quyền Admin hoạt động cuối cùng.")
            account.role = role
            account.enabled = enabled

    def change_password(self, username: str, current_password: str, new_password: str) -> None:
        self._validate_password(username, new_password)
        with self._sessions.begin() as session:
            account = session.get(SystemAccountRow, username)
            if account is None or not _verify_password(current_password, account.password_hash):
                raise ValueError("Mật khẩu hiện tại không chính xác.")
            account.password_hash = _hash_password(new_password)

    @staticmethod
    def _validate_password(username: str, password: str) -> None:
        if not username.strip() or len(password) < 12:
            raise ValueError("Tên đăng nhập bắt buộc; mật khẩu phải có ít nhất 12 ký tự.")

    def employees(self) -> tuple[dict[str, object], ...]:
        with self._sessions() as session:
            return tuple(
                {
                    "employee_id": row.employee_id,
                    "full_name": row.full_name,
                    "department": row.department,
                    "position": row.position,
                    "email": row.email,
                    "status": row.status,
                }
                for row in session.scalars(
                    select(EmployeeRow).order_by(EmployeeRow.employee_id)
                )
            )

    def save_employee(self, values: dict[str, str], employee_id: str | None = None) -> None:
        employee_id = employee_id or values["employee_id"]
        if not employee_id or not values["full_name"] or not values["email"]:
            raise ValueError("Mã nhân viên, họ tên và email là bắt buộc.")
        if values["status"] not in {"Đang làm", "Đã nghỉ"}:
            raise ValueError("Trạng thái nhân viên không hợp lệ.")
        with self._sessions.begin() as session:
            row = session.get(EmployeeRow, employee_id)
            if row is None:
                row = EmployeeRow()
                row.employee_id = employee_id
            elif employee_id != values["employee_id"]:
                raise ValueError("Không thể thay đổi mã nhân viên.")
            duplicate = session.scalar(
                select(EmployeeRow).where(
                    EmployeeRow.email == values["email"],
                    EmployeeRow.employee_id != employee_id,
                )
            )
            if duplicate is not None:
                raise ValueError("Email đã được sử dụng bởi nhân viên khác.")
            row.full_name = values["full_name"]
            row.department = values["department"]
            row.position = values["position"]
            row.email = values["email"]
            row.status = values["status"]
            if row not in session:
                session.add(row)

    def assignments(self) -> tuple[dict[str, object], ...]:
        with self._sessions() as session:
            rows = session.execute(
                select(AssignmentRow, EmployeeRow.full_name, AssetRow.model)
                .join(EmployeeRow, AssignmentRow.employee_id == EmployeeRow.employee_id)
                .join(AssetRow, AssignmentRow.asset_code == AssetRow.asset_code)
                .order_by(AssignmentRow.issued_on.desc())
            )
            return tuple(
                {
                    "assignment_id": assignment.assignment_id,
                    "asset_code": assignment.asset_code,
                    "asset_model": model,
                    "employee_id": assignment.employee_id,
                    "employee_name": name,
                    "issued_on": assignment.issued_on,
                    "due_on": assignment.due_on,
                    "returned_on": assignment.returned_on,
                    "return_condition": assignment.return_condition,
                    "status": assignment.status,
                }
                for assignment, name, model in rows
            )

    def create_assignment(
        self, assignment_id: str, asset_code: str, employee_id: str,
        issued_on: date, due_on: date | None,
    ) -> None:
        if not assignment_id or not asset_code or not employee_id:
            raise ValueError("Mã cấp phát, tài sản và nhân viên là bắt buộc.")
        if due_on is not None and due_on < issued_on:
            raise ValueError("Hạn thu hồi không thể trước ngày cấp phát.")
        with self._sessions.begin() as session:
            if session.get(AssignmentRow, assignment_id) is not None:
                raise ValueError(f"Mã cấp phát '{assignment_id}' đã tồn tại.")
            asset = session.get(AssetRow, asset_code)
            employee = session.get(EmployeeRow, employee_id)
            if asset is None:
                raise ValueError(f"Không tìm thấy tài sản '{asset_code}'.")
            if employee is None or employee.status != "Đang làm":
                raise ValueError("Chỉ nhân viên đang làm mới được nhận tài sản.")
            active_assignment = session.scalar(
                select(AssignmentRow).where(
                    AssignmentRow.asset_code == asset_code,
                    AssignmentRow.status == "Đang cấp phát",
                )
            )
            if active_assignment is not None:
                raise ValueError(f"Tài sản '{asset_code}' đang được cấp phát.")
            if asset.status != AssetStatus.AVAILABLE.value:
                raise ValueError("Chỉ tài sản sẵn sàng mới được cấp phát.")
            row = AssignmentRow()
            row.assignment_id = assignment_id
            row.asset_code = asset_code
            row.employee_id = employee_id
            row.issued_on = issued_on
            row.due_on = due_on
            row.status = "Đang cấp phát"
            session.add(row)
            asset.status = AssetStatus.IN_USE.value

    def return_assignment(self, assignment_id: str, returned_on: date, condition: str) -> None:
        if not condition.strip():
            raise ValueError("Cần ghi nhận tình trạng thiết bị khi thu hồi.")
        with self._sessions.begin() as session:
            row = session.get(AssignmentRow, assignment_id)
            if row is None:
                raise KeyError(f"Không tìm thấy phiếu cấp phát '{assignment_id}'.")
            if row.status != "Đang cấp phát":
                raise ValueError("Phiếu cấp phát này đã được thu hồi.")
            if returned_on < row.issued_on:
                raise ValueError("Ngày thu hồi không thể trước ngày cấp phát.")
            row.returned_on = returned_on
            row.return_condition = condition.strip()
            row.status = "Đã thu hồi"
            asset = session.get(AssetRow, row.asset_code)
            if asset is not None and asset.status == AssetStatus.IN_USE.value:
                asset.status = AssetStatus.AVAILABLE.value

    def inventory_runs(self) -> tuple[dict[str, object], ...]:
        with self._sessions() as session:
            rows = session.scalars(
                select(InventoryRunRow).order_by(InventoryRunRow.created_on.desc())
            ).all()
            return tuple(
                {
                    "run_id": run.run_id,
                    "created_on": run.created_on,
                    "scope": run.scope,
                    "expected_count": len(run.expected_assets),
                    "scanned_count": len(run.scans),
                    "discrepancies": self._inventory_discrepancies(run),
                }
                for run in rows
            )

    def create_inventory_run(
        self, run_id: str, created_on: date, scope_type: str, scope_value: str
    ) -> None:
        with self._sessions.begin() as session:
            if session.get(InventoryRunRow, run_id) is not None:
                raise ValueError(f"Mã đợt kiểm kê '{run_id}' đã tồn tại.")
            assets_query = select(AssetRow)
            if scope_type == "location":
                assets_query = assets_query.where(AssetRow.location == scope_value)
                scope = f"Khu vực: {scope_value}"
            elif scope_type == "category":
                assets_query = assets_query.where(AssetRow.category == scope_value)
                scope = f"Loại thiết bị: {scope_value}"
            elif scope_type == "all":
                scope = "Toàn công ty"
            else:
                raise ValueError("Phạm vi kiểm kê không hợp lệ.")
            assets = session.scalars(assets_query).all()
            if not assets:
                raise ValueError("Phạm vi này chưa có tài sản để kiểm kê.")
            run = InventoryRunRow()
            run.run_id = run_id
            run.created_on = created_on
            run.scope = scope
            expected: list[InventoryExpectedRow] = []
            for asset in assets:
                item = InventoryExpectedRow()
                item.asset_code = asset.asset_code
                item.expected_location = asset.location
                expected.append(item)
            run.expected_assets = expected
            session.add(run)

    def scan_inventory(
        self, run_id: str, asset_code: str, actual_location: str
    ) -> None:
        if not asset_code.strip() or not actual_location.strip():
            raise ValueError("Mã tài sản và vị trí thực tế là bắt buộc.")
        with self._sessions.begin() as session:
            run = session.get(InventoryRunRow, run_id)
            if run is None:
                raise KeyError(f"Không tìm thấy đợt kiểm kê '{run_id}'.")
            existing = session.scalar(
                select(InventoryScanRow).where(
                    InventoryScanRow.run_id == run_id,
                    InventoryScanRow.asset_code == asset_code.strip(),
                )
            )
            if existing is not None:
                existing.actual_location = actual_location.strip()
                return
            scan = InventoryScanRow()
            scan.run_id = run_id
            scan.asset_code = asset_code.strip()
            scan.actual_location = actual_location.strip()
            session.add(scan)

    @staticmethod
    def _inventory_discrepancies(run: InventoryRunRow) -> tuple[dict[str, str], ...]:
        expected = {item.asset_code: item.expected_location for item in run.expected_assets}
        scanned = {item.asset_code: item.actual_location for item in run.scans}
        discrepancies: list[dict[str, str]] = []
        for code in sorted(expected.keys() - scanned.keys()):
            discrepancies.append(
                {"asset_code": code, "type": "Thiếu", "expected": expected[code], "actual": ""}
            )
        for code in sorted(scanned.keys() - expected.keys()):
            discrepancies.append(
                {"asset_code": code, "type": "Thừa", "expected": "", "actual": scanned[code]}
            )
        for code in sorted(expected.keys() & scanned.keys()):
            if expected[code] != scanned[code]:
                discrepancies.append(
                    {
                        "asset_code": code,
                        "type": "Sai vị trí",
                        "expected": expected[code],
                        "actual": scanned[code],
                    }
                )
        return tuple(discrepancies)

    def licenses(self) -> tuple[dict[str, object], ...]:
        with self._sessions() as session:
            rows = session.scalars(
                select(SoftwareLicenseRow).order_by(SoftwareLicenseRow.software_name)
            ).all()
            return tuple(
                {
                    "license_id": row.license_id,
                    "software_name": row.software_name,
                    "license_type": row.license_type,
                    "quantity": row.quantity,
                    "expires_on": row.expires_on,
                    "assignments": tuple(
                        item.subject_id
                        for item in session.scalars(
                            select(LicenseAssignmentRow).where(
                                LicenseAssignmentRow.license_id == row.license_id
                            )
                        )
                    ),
                }
                for row in rows
            )

    def save_license(
        self, license_id: str, software_name: str, license_type: str,
        quantity: int, expires_on: date | None,
    ) -> None:
        if not license_id.strip() or not software_name.strip():
            raise ValueError("Mã license và tên phần mềm là bắt buộc.")
        if license_type not in {"Vĩnh viễn", "Thuê bao"} or quantity < 1:
            raise ValueError("Loại license hoặc số lượng không hợp lệ.")
        with self._sessions.begin() as session:
            row = session.get(SoftwareLicenseRow, license_id)
            if row is None:
                row = SoftwareLicenseRow()
                row.license_id = license_id
                session.add(row)
            elif quantity < len(
                session.scalars(
                    select(LicenseAssignmentRow).where(
                        LicenseAssignmentRow.license_id == license_id
                    )
                ).all()
            ):
                raise ValueError("Số lượng mới nhỏ hơn số license đang được gán.")
            row.software_name = software_name.strip()
            row.license_type = license_type
            row.quantity = quantity
            row.expires_on = expires_on

    def assign_license(self, license_id: str, subject_id: str) -> None:
        if not subject_id.strip():
            raise ValueError("Chọn người dùng hoặc thiết bị được cấp license.")
        with self._sessions.begin() as session:
            license_item = session.get(SoftwareLicenseRow, license_id)
            if license_item is None:
                raise KeyError(f"Không tìm thấy license '{license_id}'.")
            subject = session.get(EmployeeRow, subject_id.strip())
            asset = session.get(AssetRow, subject_id.strip())
            if subject is None and asset is None:
                raise ValueError("Đối tượng nhận license phải là nhân viên hoặc tài sản tồn tại.")
            if subject is not None and subject.status != "Đang làm":
                raise ValueError("Không thể gán license cho nhân viên đã nghỉ.")
            existing = session.scalar(
                select(LicenseAssignmentRow).where(
                    LicenseAssignmentRow.license_id == license_id,
                    LicenseAssignmentRow.subject_id == subject_id.strip(),
                )
            )
            if existing is not None:
                raise ValueError("Đối tượng này đã được gán license.")
            count = len(
                session.scalars(
                    select(LicenseAssignmentRow).where(
                        LicenseAssignmentRow.license_id == license_id
                    )
                ).all()
            )
            if count >= license_item.quantity:
                raise ValueError("Đã sử dụng hết số lượng license.")
            assignment = LicenseAssignmentRow()
            assignment.license_id = license_id
            assignment.subject_id = subject_id.strip()
            session.add(assignment)

    def unassign_license(self, license_id: str, subject_id: str) -> None:
        with self._sessions.begin() as session:
            row = session.scalar(
                select(LicenseAssignmentRow).where(
                    LicenseAssignmentRow.license_id == license_id,
                    LicenseAssignmentRow.subject_id == subject_id,
                )
            )
            if row is None:
                raise KeyError("Không tìm thấy đối tượng được gán license.")
            session.delete(row)

    def installations(self) -> tuple[dict[str, object], ...]:
        with self._sessions() as session:
            rows = session.execute(
                select(SoftwareInstallationRow, AssetRow.model).join(
                    AssetRow, SoftwareInstallationRow.asset_code == AssetRow.asset_code
                ).order_by(SoftwareInstallationRow.installed_on.desc())
            )
            return tuple(
                {
                    "software_name": row.software_name,
                    "asset_code": row.asset_code,
                    "asset_model": model,
                    "installed_on": row.installed_on,
                }
                for row, model in rows
            )

    def maintenance_schedules(self) -> tuple[dict[str, object], ...]:
        with self._sessions() as session:
            rows = session.execute(
                select(MaintenanceScheduleRow, AssetRow.model).join(
                    AssetRow, MaintenanceScheduleRow.asset_code == AssetRow.asset_code
                ).order_by(MaintenanceScheduleRow.due_on)
            )
            return tuple(
                {
                    "id": item.id,
                    "asset_code": item.asset_code,
                    "asset_model": model,
                    "due_on": item.due_on,
                    "interval_days": item.interval_days,
                    "notes": item.notes,
                }
                for item, model in rows
            )

    def save_maintenance_schedule(
        self, asset_code: str, due_on: date, interval_days: int, notes: str
    ) -> None:
        if interval_days < 1:
            raise ValueError("Chu kỳ bảo trì phải từ 1 ngày trở lên.")
        with self._sessions.begin() as session:
            if session.get(AssetRow, asset_code) is None:
                raise KeyError(f"Không tìm thấy tài sản '{asset_code}'.")
            row = session.scalar(
                select(MaintenanceScheduleRow).where(
                    MaintenanceScheduleRow.asset_code == asset_code
                )
            )
            if row is None:
                row = MaintenanceScheduleRow()
                row.asset_code = asset_code
                session.add(row)
            row.due_on = due_on
            row.interval_days = interval_days
            row.notes = notes.strip()

    def install_software(self, software_name: str, asset_code: str, installed_on: date) -> None:
        if not software_name.strip():
            raise ValueError("Tên phần mềm là bắt buộc.")
        with self._sessions.begin() as session:
            if session.get(AssetRow, asset_code) is None:
                raise KeyError(f"Không tìm thấy tài sản '{asset_code}'.")
            existing = session.scalar(
                select(SoftwareInstallationRow).where(
                    SoftwareInstallationRow.asset_code == asset_code,
                    SoftwareInstallationRow.software_name == software_name.strip(),
                )
            )
            if existing is not None:
                raise ValueError("Phần mềm này đã được ghi nhận trên thiết bị.")
            installation = SoftwareInstallationRow()
            installation.software_name = software_name.strip()
            installation.asset_code = asset_code
            installation.installed_on = installed_on
            session.add(installation)

    def categories(self) -> tuple[dict[str, object], ...]:
        with self._sessions() as session:
            return tuple(
                {
                    "category": row.category,
                    "values": tuple(json.loads(row.values_json)),
                }
                for row in session.scalars(
                    select(SystemCategoryRow).order_by(SystemCategoryRow.category)
                )
            )

    def save_category(self, category: str, values: list[str]) -> None:
        clean_values = sorted({value.strip() for value in values if value.strip()})
        if not category.strip() or not clean_values:
            raise ValueError("Tên danh mục và ít nhất một giá trị là bắt buộc.")
        with self._sessions.begin() as session:
            row = session.get(SystemCategoryRow, category.strip())
            if row is None:
                row = SystemCategoryRow()
                row.category = category.strip()
                session.add(row)
            row.values_json = json.dumps(clean_values, ensure_ascii=False)

    def audit_logs(self) -> tuple[dict[str, object], ...]:
        with self._sessions() as session:
            return tuple(
                {
                    "actor": row.actor,
                    "action": row.action,
                    "entity": row.entity,
                    "entity_id": row.entity_id,
                    "occurred_at": row.occurred_at,
                }
                for row in session.scalars(
                    select(AuditLogRow).order_by(AuditLogRow.occurred_at.desc()).limit(200)
                )
            )

    def record_activity(self, action: str, entity: str, entity_id: str, actor: str = "IT Admin") -> None:
        with self._sessions.begin() as session:
            row = AuditLogRow()
            row.actor = actor
            row.action = action
            row.entity = entity
            row.entity_id = entity_id
            row.occurred_at = datetime.now()
            session.add(row)

    def report_data(self) -> dict[str, object]:
        with self._sessions() as session:
            assets = session.scalars(select(AssetRow)).all()
            tickets = session.scalars(select(MaintenanceTicketRow)).all()
            licenses = session.scalars(select(SoftwareLicenseRow)).all()
            assignments = session.scalars(select(AssignmentRow)).all()
            employees = {
                row.employee_id: row for row in session.scalars(select(EmployeeRow))
            }
            active_owners = {
                row.asset_code: employees[row.employee_id].department
                for row in assignments
                if row.status == "Đang cấp phát" and row.employee_id in employees
            }
            return {
                "assets": tuple(
                    {
                        "asset_code": row.asset_code,
                        "category": row.category,
                        "status": row.status,
                        "location": row.location,
                        "value": row.value,
                        "warranty_until": row.warranty_until,
                        "department": active_owners.get(row.asset_code, "Chưa cấp phát"),
                    }
                    for row in assets
                ),
                "maintenance": tuple(
                    {
                        "ticket_id": row.ticket_id,
                        "asset_code": row.asset_code,
                        "received_on": row.received_on,
                        "cost": row.cost,
                    }
                    for row in tickets
                ),
                "licenses": tuple(
                    {
                        "license_id": row.license_id,
                        "software_name": row.software_name,
                        "expires_on": row.expires_on,
                        "quantity": row.quantity,
                    }
                    for row in licenses
                ),
                "assignments": tuple(
                    {
                        "assignment_id": row.assignment_id,
                        "asset_code": row.asset_code,
                        "employee_id": row.employee_id,
                        "employee_name": employees[row.employee_id].full_name,
                        "due_on": row.due_on,
                        "status": row.status,
                    }
                    for row in assignments
                ),
            }

def _snapshot_from_json(raw: str) -> tuple[tuple[str, str], ...]:
    values = json.loads(raw)
    if not isinstance(values, list) or any(
        not isinstance(item, list)
        or len(item) != 2
        or not all(isinstance(part, str) for part in item)
        for item in values
    ):
        raise ValueError("Invalid asset history snapshot stored in the database.")
    return tuple((item[0], item[1]) for item in values)


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

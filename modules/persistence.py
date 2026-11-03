import json
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

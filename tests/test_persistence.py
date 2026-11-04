import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import inspect

from modules.asset_management.models import Asset, AssetStatus
from modules.database import Database
from modules.maintenance.models import MaintenanceTicket, MaintenanceType
from modules.persistence import SQLAssetModel, SQLMaintenanceModel, SQLModuleModel
from webapp.controllers import WebController


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = Database("sqlite+pysqlite:///:memory:", create_database=False)
        self.database.initialize()

    def tearDown(self) -> None:
        self.database.close()

    def test_initialization_creates_tables_for_all_modules(self) -> None:
        tables = set(inspect(self.database.engine).get_table_names())

        self.assertTrue(
            {
                "assets",
                "asset_changes",
                "asset_attachments",
                "assignments",
                "maintenance_tickets",
                "inventory_runs",
                "software_licenses",
                "employees",
                "system_accounts",
                "audit_logs",
                "system_categories",
                "inventory_expected_assets",
                "maintenance_schedules",
            }.issubset(tables)
        )

    def test_asset_and_maintenance_data_survive_repository_recreation(self) -> None:
        assets = SQLAssetModel(self.database)
        maintenance = SQLMaintenanceModel(self.database)
        asset = Asset(
            "IT-DB-1",
            "SN-DB-1",
            "Máy tính xách tay",
            "Nhà sản xuất thử nghiệm",
            date(2026, 1, 1),
            Decimal("1234.50"),
            None,
            "Kho thiết bị",
            AssetStatus.AVAILABLE,
            "Máy tính",
            attachments=["invoice.pdf"],
        )
        assets.create(asset)
        assets.update("IT-DB-1", location="Văn phòng tầng 2")
        maintenance.create_ticket(
            MaintenanceTicket(
                "MT-DB-1",
                "IT-DB-1",
                MaintenanceType.REPAIR,
                date(2026, 2, 1),
                "Sửa chữa lỗi màn hình",
                "Kỹ thuật viên",
                Decimal("250.00"),
                ["Ổ cứng SSD"],
            )
        )

        reloaded_asset = SQLAssetModel(self.database).get("IT-DB-1")
        reloaded_ticket = SQLMaintenanceModel(self.database).get_all()[0]

        self.assertEqual("Văn phòng tầng 2", reloaded_asset.location)
        self.assertEqual(2, len(reloaded_asset.history))
        self.assertEqual(["invoice.pdf"], reloaded_asset.attachments)
        self.assertEqual("Máy tính xách tay", reloaded_asset.model)
        self.assertEqual("Nhà sản xuất thử nghiệm", reloaded_asset.manufacturer)
        self.assertEqual(Decimal("250.00"), reloaded_ticket.cost)
        self.assertEqual("Sửa chữa lỗi màn hình", reloaded_ticket.issue_description)
        self.assertEqual(["Ổ cứng SSD"], reloaded_ticket.replacement_parts)

    def test_sql_server_environment_settings_build_connection_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "SQL_SERVER_HOST=192.168.1.69\n"
                "SQL_SERVER_DATABASE=ITmanager\n"
                "SQL_SERVER_AUTH=sql\n"
                "SQL_SERVER_USER=itmanager-user\n"
                "SQL_SERVER_PASSWORD=secret-for-test\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                database = Database.from_env(env_path)

        self.assertEqual("mssql", database.url.get_backend_name())
        self.assertEqual("192.168.1.69", database.url.host)
        self.assertEqual("ITmanager", database.url.database)
        self.assertEqual("itmanager-user", database.url.username)
        self.assertNotIn("secret-for-test", database.url.render_as_string(hide_password=True))

    def test_sql_auth_requires_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("SQL_SERVER_AUTH=sql\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, "SQL_SERVER_USER"):
                    Database.from_env(env_path)

    def test_file_database_survives_database_reinitialization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            url = f"sqlite+pysqlite:///{Path(directory) / 'ITmanager.db'}"
            first_database = Database(url, create_database=False)
            first_database.initialize()
            SQLAssetModel(first_database).create(
                Asset(
                    "IT-PERSIST",
                    "SN-1",
                    "Laptop",
                    "Vendor",
                    date(2026, 1, 1),
                    Decimal("50"),
                    None,
                    "Office",
                    AssetStatus.AVAILABLE,
                    "Computer",
                )
            )
            first_database.close()

            second_database = Database(url, create_database=False)
            second_database.initialize()
            try:
                self.assertEqual(
                    "IT-PERSIST",
                    SQLAssetModel(second_database).get_all()[0].asset_code,
                )
            finally:
                second_database.close()

    def test_module_workflows_persist_and_validate_related_records(self) -> None:
        modules = SQLModuleModel(self.database)
        assets = SQLAssetModel(self.database)
        assets.create(
            Asset(
                "IT-FLOW-1", "SN-FLOW-1", "Máy tính", "Hãng", date(2026, 1, 1),
                Decimal("100"), date(2027, 1, 1), "Văn phòng", AssetStatus.AVAILABLE, "Máy tính",
            )
        )
        modules.save_employee(
            {
                "employee_id": "NV-FLOW-1",
                "full_name": "Nguyễn Văn A",
                "department": "IT",
                "position": "Kỹ thuật",
                "email": "nv-flow-1@example.test",
                "status": "Đang làm",
            }
        )
        modules.create_assignment(
            "AS-FLOW-1", "IT-FLOW-1", "NV-FLOW-1", date(2026, 2, 1), date(2026, 3, 1)
        )
        self.assertEqual("Đang dùng", assets.get("IT-FLOW-1").status.value)
        with self.assertRaisesRegex(ValueError, "đang được cấp phát"):
            modules.create_assignment(
                "AS-FLOW-2", "IT-FLOW-1", "NV-FLOW-1", date(2026, 2, 1), None
            )
        modules.return_assignment("AS-FLOW-1", date(2026, 2, 15), "Đã kiểm tra")
        self.assertEqual("Sẵn sàng", assets.get("IT-FLOW-1").status.value)

        modules.create_inventory_run("KK-FLOW-1", date(2026, 2, 1), "all", "")
        modules.scan_inventory("KK-FLOW-1", "IT-FLOW-1", "Kho")
        modules.scan_inventory("KK-FLOW-1", "IT-EXTRA", "Kho")
        discrepancies = modules.inventory_runs()[0]["discrepancies"]
        self.assertEqual({"Sai vị trí", "Thừa"}, {item["type"] for item in discrepancies})

        modules.save_license("LIC-FLOW-1", "Office", "Thuê bao", 1, date(2027, 1, 1))
        modules.assign_license("LIC-FLOW-1", "NV-FLOW-1")
        with self.assertRaisesRegex(ValueError, "hết số lượng"):
            modules.assign_license("LIC-FLOW-1", "IT-FLOW-1")
        modules.install_software("Office", "IT-FLOW-1", date(2026, 2, 1))
        modules.save_maintenance_schedule(
            "IT-FLOW-1", date(2026, 4, 1), 180, "Vệ sinh và kiểm tra định kỳ"
        )
        self.assertEqual(date(2026, 4, 1), modules.maintenance_schedules()[0]["due_on"])
        modules.save_category("Vị trí", ["Kho", "Văn phòng"])
        modules.record_activity("Cấp phát", "Phiếu", "AS-FLOW-1")
        modules.bootstrap_admin(
            "admin", "secure-password-123", "NV-ADMIN", "Quản trị", "admin@example.test"
        )
        self.assertEqual("Admin", modules.authenticate("admin", "secure-password-123"))
        self.assertIsNone(modules.authenticate("admin", "incorrect-password"))
        modules.save_account(
            "staff", "NV-FLOW-1", "staff-password-123", "IT Staff"
        )
        self.assertEqual("IT Staff", modules.authenticate("staff", "staff-password-123"))
        modules.change_password("staff", "staff-password-123", "new-staff-password-123")
        self.assertIsNone(modules.authenticate("staff", "staff-password-123"))
        self.assertEqual("IT Staff", modules.authenticate("staff", "new-staff-password-123"))

        self.assertEqual(("Kho", "Văn phòng"), modules.categories()[0]["values"])
        self.assertEqual("Sẵn sàng", assets.get("IT-FLOW-1").status.value)
        self.assertEqual("Office", modules.installations()[0]["software_name"])
        self.assertTrue(modules.audit_logs())
        controller = WebController(
            assets, SQLMaintenanceModel(self.database), modules
        )
        for path in (
            "/assets", "/assignment", "/maintenance", "/inventory", "/software",
            "/employees", "/reports", "/system",
        ):
            status, html = controller.page(path)
            self.assertEqual(200, status, path)
            self.assertIn("<html", html)
        filename, report = controller.export("/inventory/export/KK-FLOW-1.csv")
        self.assertEqual("inventory_KK-FLOW-1.csv", filename)
        self.assertIn("Sai vị trí", report)


if __name__ == "__main__":
    unittest.main()

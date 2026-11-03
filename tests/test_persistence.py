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
from modules.persistence import SQLAssetModel, SQLMaintenanceModel


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


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date
from decimal import Decimal

from modules.asset_management.models import Asset, AssetModel, AssetStatus
from modules.assignment.models import Assignment, AssignmentModel
from modules.inventory.models import DiscrepancyType, InventoryRun
from modules.maintenance.models import MaintenanceModel
from modules.reporting.models import ReportingModel
from modules.software_license.models import LicenseType, SoftwareLicense
from modules.system.models import Permission, SystemModel
from modules.employee.models import UserRole


class ModuleTests(unittest.TestCase):
    def test_asset_crud_keeps_change_history(self) -> None:
        model = AssetModel()
        asset = Asset(
            asset_code="IT-001",
            serial_number="SN-1",
            model="Laptop",
            manufacturer="Vendor",
            purchase_date=date(2025, 1, 1),
            value=Decimal("1000"),
            warranty_until=None,
            location="Office",
            status=AssetStatus.AVAILABLE,
            category="Máy tính",
        )
        model.create(asset)
        updated = model.update("IT-001", location="Kho")

        self.assertEqual("Kho", updated.location)
        self.assertEqual(2, len(updated.history))
        self.assertIn(("location", "'Office'"), updated.history[-1].before)
        self.assertIn(("location", "'Kho'"), updated.history[-1].after)
        model.delete("IT-001")
        self.assertEqual((), model.get_all())

    def test_asset_cannot_be_assigned_twice(self) -> None:
        model = AssignmentModel()
        model.assign(Assignment("AS-1", "IT-001", "NV-1", date(2026, 1, 1)))

        with self.assertRaises(ValueError):
            model.assign(Assignment("AS-2", "IT-001", "NV-2", date(2026, 1, 2)))

    def test_inventory_compares_presence_and_location(self) -> None:
        run = InventoryRun("KK-1", date(2026, 1, 1), "Toàn công ty", {"IT-1": "A", "IT-2": "B"})
        run.scan("IT-1", "C")
        run.scan("IT-3", "A")

        self.assertEqual(
            {DiscrepancyType.MISSING, DiscrepancyType.EXTRA, DiscrepancyType.WRONG_LOCATION},
            {item.discrepancy_type for item in run.discrepancies()},
        )

    def test_role_permissions_are_explicit(self) -> None:
        model = SystemModel()

        self.assertTrue(model.has_permission(UserRole.ADMIN, Permission.DELETE))
        self.assertFalse(model.has_permission(UserRole.VIEWER, Permission.DELETE))

    def test_maintenance_and_license_expiration_alerts(self) -> None:
        today = date(2026, 1, 1)
        warranty_dates = {"IT-1": date(2026, 1, 10), "IT-2": date(2027, 1, 1)}
        license_item = SoftwareLicense(
            "LIC-1", "Office", LicenseType.SUBSCRIPTION, 5, date(2026, 1, 10)
        )

        self.assertEqual(("IT-1",), MaintenanceModel.warranty_expiring(warranty_dates, today))
        self.assertTrue(license_item.is_expiring(today))
        self.assertFalse(license_item.is_expiring(date(2026, 2, 1)))

    def test_reporting_summarizes_assets_and_costs(self) -> None:
        asset = Asset(
            "IT-001", "SN-1", "Laptop", "Vendor", date(2025, 1, 1),
            Decimal("1000"), None, "Office", AssetStatus.AVAILABLE, "Máy tính",
        )
        summary = ReportingModel.summarize_assets((asset,))

        self.assertEqual({"Máy tính": 1}, summary.by_category)
        self.assertEqual(Decimal("25"), ReportingModel.total_repair_cost((Decimal("10"), Decimal("15"))))


if __name__ == "__main__":
    unittest.main()

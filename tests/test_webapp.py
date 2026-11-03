import unittest
from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from modules.asset_management.models import Asset, AssetModel, AssetStatus
from modules.maintenance.models import MaintenanceModel, MaintenanceType
from webapp.controllers import WebController


class WebApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assets = AssetModel()
        self.assets.create(
            Asset(
                "IT-001",
                "SN-001",
                "Laptop",
                "Vendor",
                date(2025, 1, 1),
                Decimal("1000"),
                None,
                "Office",
                AssetStatus.AVAILABLE,
                "Máy tính",
            )
        )
        self.maintenance = MaintenanceModel()
        self.controller = WebController(self.assets, self.maintenance)

    def test_dashboard_and_module_navigation_render(self) -> None:
        status, html = self.controller.page("/")

        self.assertEqual(200, status)
        self.assertIn("Tổng quan", html)
        self.assertIn("IT-001", html)
        self.assertIn('href="/maintenance"', html)

    def test_asset_form_creates_searchable_asset(self) -> None:
        redirect = self.controller.submit(
            "/assets",
            {
                "asset_code": "IT-002",
                "serial_number": "SN-002",
                "model": "Máy in",
                "manufacturer": "Vendor",
                "purchase_date": "2026-01-01",
                "value": "2000",
                "location": "Kho",
                "status": "Sẵn sàng",
                "category": "Máy in",
            },
        )
        status, html = self.controller.page("/assets", query="IT-002")

        self.assertEqual(
            "Đã thêm tài sản.",
            parse_qs(urlsplit(redirect).query)["notice"][0],
        )
        self.assertEqual(200, status)
        self.assertIn("IT-002", html)
        self.assertNotIn('<span class="asset-id">IT-001</span>', html)

    def test_maintenance_ticket_can_be_created_and_completed(self) -> None:
        self.controller.submit(
            "/maintenance",
            {
                "ticket_id": "MT-001",
                "asset_code": "IT-001",
                "maintenance_type": "repair",
                "received_on": "2026-01-02",
                "issue_description": "Thay ổ cứng",
                "handler": "IT Staff",
                "cost": "500",
                "replacement_parts": "SSD",
            },
        )
        ticket = self.maintenance.get_all()[0]
        self.assertEqual(MaintenanceType.REPAIR, ticket.maintenance_type)
        self.assertEqual(["SSD"], ticket.replacement_parts)

        self.controller.submit("/maintenance/MT-001/complete", {})

        self.assertIsNotNone(ticket.completed_on)
        self.assertIn("Hoàn thành", self.controller.page("/maintenance")[1])

    def test_invalid_form_and_unknown_route_return_errors(self) -> None:
        with self.assertRaises(ValueError):
            self.controller.submit("/assets", {"asset_code": "IT-001", "model": "Duplicate"})

        status, html = self.controller.page("/missing")
        self.assertEqual(404, status)
        self.assertIn("Không tìm thấy trang", html)

    def test_error_message_is_html_escaped(self) -> None:
        status, html = self.controller.page("/assets", error="<script>alert(1)</script>")

        self.assertEqual(400, status)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_asset_form_rejects_non_finite_values(self) -> None:
        with self.assertRaises(ValueError):
            self.controller.submit(
                "/assets",
                {
                    "asset_code": "IT-NAN",
                    "model": "Laptop",
                    "category": "Máy tính",
                    "location": "Kho",
                    "value": "NaN",
                },
            )


if __name__ == "__main__":
    unittest.main()

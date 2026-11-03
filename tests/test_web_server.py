import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from webapp.server import build_controller, make_handler


class WebServerTests(unittest.TestCase):
    def test_http_pages_and_asset_creation(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(build_controller()))
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(f"{base_url}/") as response:
                self.assertEqual(200, response.status)
                self.assertIn("font-src https://fonts.gstatic.com", response.headers["Content-Security-Policy"])
                page = response.read().decode("utf-8")
                self.assertIn("Tổng quan", page)
                self.assertIn("Plus+Jakarta+Sans", page)

            with urlopen(f"{base_url}/static/style.css") as response:
                self.assertEqual("text/css; charset=utf-8", response.headers["Content-Type"])
                stylesheet = response.read().decode("utf-8")
                self.assertIn("html { font-size: 62.5%; }", stylesheet)
                self.assertIn("font-size: 1.6rem;", stylesheet)
                self.assertIn("font-family: \"Plus Jakarta Sans\", sans-serif", stylesheet)
                self.assertIn('"Plus Jakarta Sans", sans-serif', stylesheet)

            form = urlencode(
                {
                    "asset_code": "IT-WEB",
                    "model": "Laptop",
                    "category": "Máy tính",
                    "location": "Văn phòng",
                    "status": "Sẵn sàng",
                    "value": "1000",
                }
            ).encode("utf-8")
            request = Request(
                f"{base_url}/assets",
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urlopen(request) as response:
                self.assertEqual(200, response.status)
                self.assertIn("IT-WEB", response.read().decode("utf-8"))

            ticket_form = urlencode(
                {
                    "ticket_id": "MT-WEB",
                    "asset_code": "IT-WEB",
                    "maintenance_type": "repair",
                    "received_on": "2026-11-03",
                    "issue_description": "Kiểm tra thiết bị",
                    "handler": "IT Staff",
                    "cost": "250000",
                    "replacement_parts": "SSD",
                }
            ).encode("utf-8")
            ticket_request = Request(
                f"{base_url}/maintenance",
                data=ticket_form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urlopen(ticket_request) as response:
                self.assertIn("MT-WEB", response.read().decode("utf-8"))

            complete_request = Request(
                f"{base_url}/maintenance/MT-WEB/complete",
                data=b"",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urlopen(complete_request) as response:
                self.assertIn("Hoàn thành", response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()

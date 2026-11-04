import threading
import tempfile
import unittest
from pathlib import Path
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

from modules.database import Database
from modules.persistence import SQLAssetModel, SQLMaintenanceModel, SQLModuleModel
from webapp.controllers import WebController
from webapp.server import _parse_multipart_form, build_controller, make_handler


class WebServerTests(unittest.TestCase):
    def test_multipart_upload_stores_supported_file_with_generated_name(self) -> None:
        boundary = "itmanager-test-boundary"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="asset_code"\r\n\r\n'
            "IT-UPLOAD\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="files"; filename="../../invoice.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
            "test document\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")
        fields, paths = _parse_multipart_form(
            body, f"multipart/form-data; boundary={boundary}"
        )
        try:
            self.assertEqual("IT-UPLOAD", fields["asset_code"])
            self.assertEqual(1, len(paths))
            self.assertTrue(paths[0].is_file())
            self.assertEqual(b"test document", paths[0].read_bytes())
            self.assertEqual(1, len(fields["attachments"].splitlines()))
        finally:
            for path in paths:
                path.unlink(missing_ok=True)

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

    def test_database_web_app_bootstraps_login_and_protects_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(
                f"sqlite+pysqlite:///{Path(directory) / 'auth.db'}",
                create_database=False,
            )
            database.initialize()
            controller = WebController(
                SQLAssetModel(database),
                SQLMaintenanceModel(database),
                SQLModuleModel(database),
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(controller))
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            opener = build_opener(HTTPCookieProcessor(CookieJar()))
            base_url = f"http://127.0.0.1:{server.server_port}"
            stored_upload = None
            try:
                with opener.open(f"{base_url}/") as response:
                    self.assertTrue(response.geturl().endswith("/setup"))
                setup = urlencode(
                    {
                        "username": "admin",
                        "password": "secure-password-123",
                        "employee_id": "NV-ADMIN",
                        "full_name": "Quản trị",
                        "email": "admin@example.test",
                    }
                ).encode("utf-8")
                with opener.open(
                    Request(
                        f"{base_url}/setup",
                        data=setup,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
                ) as response:
                    self.assertIn("Tổng quan", response.read().decode("utf-8"))
                with opener.open(f"{base_url}/employees") as response:
                    self.assertIn("Quản trị", response.read().decode("utf-8"))
                boundary = "authenticated-upload"
                parts = []
                for name, value in {
                    "asset_code": "IT-AUTH-UPLOAD",
                    "model": "Máy in",
                    "category": "Máy in",
                    "location": "Kho",
                    "value": "1000",
                }.items():
                    parts.append(
                        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n"
                    )
                parts.append(
                    f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"invoice.txt\"\r\n"
                    "Content-Type: text/plain\r\n\r\nHóa đơn kiểm thử\r\n"
                )
                parts.append(f"--{boundary}--\r\n")
                upload_request = Request(
                    f"{base_url}/assets",
                    data="".join(parts).encode("utf-8"),
                    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                )
                with opener.open(upload_request) as response:
                    self.assertIn("IT-AUTH-UPLOAD", response.read().decode("utf-8"))
                stored_upload = controller._assets.get("IT-AUTH-UPLOAD").attachments[0]
                with opener.open(f"{base_url}/{stored_upload}") as response:
                    self.assertEqual("Hóa đơn kiểm thử", response.read().decode("utf-8"))
                logout = Request(
                    f"{base_url}/logout",
                    data=b"",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                with opener.open(logout) as response:
                    self.assertTrue(response.geturl().endswith("/login"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                database.close()
                if stored_upload:
                    (Path(__file__).resolve().parents[1] / "webapp" / stored_upload).unlink(
                        missing_ok=True
                    )


if __name__ == "__main__":
    unittest.main()

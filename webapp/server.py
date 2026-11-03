import argparse
from datetime import date
from decimal import Decimal
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from modules.asset_management.models import Asset, AssetModel, AssetStatus
from modules.maintenance.models import MaintenanceModel
from webapp.controllers import WebController, parse_form


ROOT = Path(__file__).resolve().parent
MAX_FORM_BYTES = 64 * 1024


def build_controller() -> WebController:
    assets = AssetModel()
    assets.create(
        Asset(
            asset_code="IT-001",
            serial_number="SN-0001",
            model="Laptop văn phòng",
            manufacturer="Dell",
            purchase_date=date(2025, 6, 12),
            value=Decimal("18500000"),
            warranty_until=date(2027, 6, 12),
            location="Văn phòng · Tầng 2",
            status=AssetStatus.IN_USE,
            category="Máy tính",
        )
    )
    assets.create(
        Asset(
            asset_code="IT-002",
            serial_number="SN-0002",
            model="Máy in Laser",
            manufacturer="HP",
            purchase_date=date(2025, 9, 8),
            value=Decimal("7200000"),
            warranty_until=date(2026, 9, 8),
            location="Phòng hành chính",
            status=AssetStatus.AVAILABLE,
            category="Máy in",
        )
    )
    return WebController(assets, MaintenanceModel())


def make_handler(controller: WebController):
    class ITmanagerHandler(BaseHTTPRequestHandler):
        server_version = "ITmanager"
        sys_version = ""

        def do_GET(self) -> None:
            request = urlsplit(self.path)
            if request.path == "/static/style.css":
                self._send_static()
                return
            values = parse_qs(request.query, encoding="utf-8")
            status, html = controller.page(
                request.path,
                str(values.get("q", [""])[-1]),
                str(values.get("notice", [""])[-1]),
            )
            self._send(status, html.encode("utf-8"), "text/html; charset=utf-8")

        def do_POST(self) -> None:
            try:
                content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                if content_type != "application/x-www-form-urlencoded":
                    raise ValueError("Định dạng biểu mẫu không được hỗ trợ.")
                raw_length = self.headers.get("Content-Length", "")
                if not raw_length.isdigit():
                    raise ValueError("Thiếu độ dài dữ liệu biểu mẫu.")
                length = int(raw_length)
                if length > MAX_FORM_BYTES:
                    self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b"Form too large", "text/plain")
                    return
                fields = parse_form(self.rfile.read(length))
                location = controller.submit(urlsplit(self.path).path, fields)
            except (ValueError, KeyError) as error:
                target = urlsplit(self.path).path
                if target in {"/assets", "/maintenance"}:
                    status, html = controller.page(target, error=str(error))
                else:
                    status, html = HTTPStatus.BAD_REQUEST, controller.render_error(str(error))
                self._send(status, html.encode("utf-8"), "text/html; charset=utf-8")
                return
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def _send_static(self) -> None:
            css_path = ROOT / "static" / "style.css"
            try:
                content = css_path.read_bytes()
            except OSError:
                self._send(HTTPStatus.NOT_FOUND, b"Stylesheet not found", "text/plain")
                return
            self._send(HTTPStatus.OK, content, "text/css; charset=utf-8")

        def _send(self, status: int, content: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'")
            self.send_header("Referrer-Policy", "same-origin")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

    return ITmanagerHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ITmanager web application.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default: 8000)")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    server = ThreadingHTTPServer((args.host, args.port), make_handler(build_controller()))
    print(f"ITmanager đang chạy tại http://{args.host}:{args.port} (Ctrl+C để dừng)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng ITmanager...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

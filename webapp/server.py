import argparse
import logging
import re
import secrets
import uuid
from datetime import date
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from html import escape
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from sqlalchemy.exc import SQLAlchemyError

from modules.asset_management.models import Asset, AssetModel, AssetStatus
from modules.maintenance.models import MaintenanceModel
from modules.database import Database
from modules.persistence import SQLAssetModel, SQLMaintenanceModel, SQLModuleModel
from webapp.controllers import WebController, parse_form


ROOT = Path(__file__).resolve().parent
MAX_FORM_BYTES = 64 * 1024
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".txt"}


def build_controller(database: Database | None = None) -> WebController:
    if database is not None:
        return WebController(
            SQLAssetModel(database),
            SQLMaintenanceModel(database),
            SQLModuleModel(database),
        )

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
    sessions: dict[str, tuple[str, str]] = {}

    class ITmanagerHandler(BaseHTTPRequestHandler):
        server_version = "ITmanager"
        sys_version = ""

        def do_GET(self) -> None:
            request = urlsplit(self.path)
            session = self._session()
            auth_enabled = controller._modules is not None
            if auth_enabled and request.path in {"/login", "/setup"}:
                if self._modules().account_count() and request.path == "/setup":
                    self._redirect("/login")
                    return
                if session is not None:
                    self._redirect("/")
                    return
                self._send_auth_page(request.path)
                return
            if auth_enabled and request.path not in {"/static/style.css"} and session is None:
                if self._modules().account_count() == 0:
                    self._redirect("/setup")
                else:
                    self._redirect("/login")
                return
            if request.path == "/static/style.css":
                self._send_static()
                return
            upload_match = re.fullmatch(r"/uploads/([A-Za-z0-9_.-]+)", request.path)
            if upload_match:
                path = (ROOT / "uploads" / upload_match.group(1)).resolve()
                upload_root = (ROOT / "uploads").resolve()
                if path.parent != upload_root or not path.is_file():
                    self._send(HTTPStatus.NOT_FOUND, b"File not found", "text/plain")
                    return
                content_type = guess_type(path.name)[0] or "application/octet-stream"
                self._send(HTTPStatus.OK, path.read_bytes(), content_type)
                return
            if request.path.startswith("/reports/export/") or request.path.startswith(
                "/inventory/export/"
            ):
                try:
                    filename, content = controller.export(request.path)
                except ValueError as error:
                    self._send(
                        HTTPStatus.NOT_FOUND,
                        str(error).encode("utf-8"),
                        "text/plain; charset=utf-8",
                    )
                    return
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header(
                    "Content-Disposition", f'attachment; filename="{filename}"'
                )
                self.send_header("Content-Length", str(len(content.encode("utf-8"))))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                return
            values = parse_qs(request.query, encoding="utf-8")
            status, html = controller.page(
                request.path,
                str(values.get("q", [""])[-1]),
                str(values.get("notice", [""])[-1]),
            )
            if session is not None:
                username, role = session
                html = html.replace(
                    '<div class="profile">',
                    f'<div class="profile">{escape(username)} · {escape(role)}'
                    '<form method="post" action="/system/password">'
                    '<input type="password" name="current_password" required placeholder="Mật khẩu hiện tại">'
                    '<input type="password" name="new_password" minlength="12" required placeholder="Mật khẩu mới">'
                    '<button class="text-button">Đổi mật khẩu</button></form>'
                    '<form method="post" action="/logout"><button class="text-button">Đăng xuất</button></form>',
                    1,
                )
            self._send(status, html.encode("utf-8"), "text/html; charset=utf-8")

        def do_POST(self) -> None:
            uploaded_paths: list[Path] = []
            try:
                target = urlsplit(self.path).path
                if (
                    controller._modules is not None
                    and target not in {"/login", "/setup", "/logout"}
                ):
                    session = self._session()
                    if session is None:
                        self._redirect(
                            "/setup" if self._modules().account_count() == 0 else "/login"
                        )
                        return
                    if session[1] == "Viewer" and target != "/system/password":
                        self._send(HTTPStatus.FORBIDDEN, b"Viewer is read-only", "text/plain")
                        return
                    if target in {
                        "/system/categories", "/system/accounts", "/system/accounts/access"
                    } and session[1] != "Admin":
                        self._send(HTTPStatus.FORBIDDEN, b"Admin role required", "text/plain")
                        return
                content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                if content_type not in {
                    "application/x-www-form-urlencoded",
                    "multipart/form-data",
                }:
                    raise ValueError("Định dạng biểu mẫu không được hỗ trợ.")
                raw_length = self.headers.get("Content-Length", "")
                if not raw_length.isdigit():
                    raise ValueError("Thiếu độ dài dữ liệu biểu mẫu.")
                length = int(raw_length)
                max_length = MAX_UPLOAD_BYTES if content_type == "multipart/form-data" else MAX_FORM_BYTES
                if length > max_length:
                    self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b"Form too large", "text/plain")
                    return
                body = self.rfile.read(length)
                if content_type == "multipart/form-data":
                    fields, uploaded_paths = _parse_multipart_form(
                        body, self.headers.get("Content-Type", "")
                    )
                else:
                    fields = parse_form(body)
                if target == "/logout":
                    token = self._session_token()
                    if token:
                        sessions.pop(token, None)
                    self.send_response(HTTPStatus.SEE_OTHER)
                    self.send_header("Location", "/login")
                    self.send_header(
                        "Set-Cookie",
                        "itmanager_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0",
                    )
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if controller._modules is not None and target in {"/login", "/setup"}:
                    modules = self._modules()
                    if target == "/setup":
                        modules.bootstrap_admin(
                            fields.get("username", ""),
                            fields.get("password", ""),
                            fields.get("employee_id", ""),
                            fields.get("full_name", ""),
                            fields.get("email", ""),
                        )
                        role = "Admin"
                        username = fields.get("username", "").strip()
                    else:
                        username = fields.get("username", "").strip()
                        role = modules.authenticate(username, fields.get("password", ""))
                        if role is None:
                            self._send_auth_page("/login", "Tên đăng nhập hoặc mật khẩu không chính xác.", HTTPStatus.UNAUTHORIZED)
                            return
                    token = secrets.token_urlsafe(32)
                    sessions[token] = (username, role)
                    self.send_response(HTTPStatus.SEE_OTHER)
                    self.send_header("Location", "/")
                    self.send_header(
                        "Set-Cookie",
                        f"itmanager_session={token}; Path=/; HttpOnly; SameSite=Lax",
                    )
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                session = self._session()
                if controller._modules is not None and session is None:
                    self._redirect("/login")
                    return
                if session is not None:
                    username, role = session
                    if role == "Viewer" and target not in {"/system/password"}:
                        raise ValueError("Tài khoản Viewer chỉ được xem dữ liệu.")
                    if target in {
                        "/system/categories", "/system/accounts", "/system/accounts/access"
                    } and role != "Admin":
                        raise ValueError("Chỉ Admin được quản trị tài khoản và danh mục.")
                    if target == "/system/password":
                        fields["_session_username"] = username
                location = controller.submit(urlsplit(self.path).path, fields)
            except (ValueError, KeyError) as error:
                for path in uploaded_paths:
                    path.unlink(missing_ok=True)
                target = urlsplit(self.path).path
                if target in {"/assets", "/maintenance"}:
                    status, html = controller.page(target, error=str(error))
                else:
                    status, html = HTTPStatus.BAD_REQUEST, controller.render_error(str(error))
                self._send(status, html.encode("utf-8"), "text/html; charset=utf-8")
                return
            except SQLAlchemyError:
                for path in uploaded_paths:
                    path.unlink(missing_ok=True)
                logging.exception("Database operation failed while processing %s", self.path)
                self._send(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    "Không thể lưu dữ liệu do lỗi cơ sở dữ liệu.".encode("utf-8"),
                    "text/plain; charset=utf-8",
                )
                return
            except Exception:
                for path in uploaded_paths:
                    path.unlink(missing_ok=True)
                raise
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def _session_token(self) -> str | None:
            cookie = SimpleCookie()
            cookie.load(self.headers.get("Cookie", ""))
            morsel = cookie.get("itmanager_session")
            return morsel.value if morsel else None

        def _session(self) -> tuple[str, str] | None:
            token = self._session_token()
            current = sessions.get(token) if token else None
            if current is None or controller._modules is None:
                return current
            username, _ = current
            role = controller._modules.account_role(username)
            if role is None:
                sessions.pop(token, None)
                return None
            sessions[token] = (username, role)
            return username, role

        @staticmethod
        def _modules():
            if controller._modules is None:
                raise RuntimeError("Account management requires a configured database.")
            return controller._modules

        def _redirect(self, location: str) -> None:
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _send_auth_page(self, path: str, error: str = "", status: int = HTTPStatus.OK) -> None:
            from html import escape
            from webapp.views import _shell

            if path == "/setup":
                title = "Admin Setup"
                heading = "T&#7841;o t&#224;i kho&#7843;n Admin &#273;&#7847;u ti&#234;n"
                intro = (
                    "T&#7841;o t&#224;i kho&#7843;n qu&#7843;n tr&#7883; &#273;&#7875; b&#7843;o v&#7879; "
                    "d&#7919; li&#7879;u v&#224; b&#7855;t &#273;&#7847;u d&#249;ng c&#225;c ph&#226;n h&#7879;."
                )
                fields = (
                    '<label>T&#234;n &#273;&#259;ng nh&#7853;p<input name="username" required autocomplete="username"></label>'
                    '<label>M&#7853;t kh&#7849;u (t&#7889;i thi&#7875;u 12 k&#253; t&#7921;)<input type="password" name="password" minlength="12" required autocomplete="new-password"></label>'
                    '<label>M&#227; nh&#226;n vi&#234;n<input name="employee_id" required autocomplete="off"></label>'
                    '<label>H&#7885; v&#224; t&#234;n<input name="full_name" required autocomplete="name"></label>'
                    '<label>Email<input type="email" name="email" required autocomplete="email"></label>'
                )
            else:
                title = "Sign in"
                heading = "&#272;&#259;ng nh&#7853;p ITmanager"
                intro = "&#272;&#259;ng nh&#7853;p &#273;&#7875; ti&#7871;p t&#7909;c qu&#7843;n l&#253; IT."
                fields = (
                    '<label>T&#234;n &#273;&#259;ng nh&#7853;p<input name="username" required autofocus autocomplete="username"></label>'
                    '<label>M&#7853;t kh&#7849;u<input type="password" name="password" required autocomplete="current-password"></label>'
                )
            notice = f'<div class="notice error" role="alert">{escape(error)}</div>' if error else ""
            content = (
                '<div class="auth-brand"><span class="auth-brand-mark">IT</span>'
                '<span><strong>ITmanager</strong><small>ASSET OPERATIONS</small></span></div>'
                '<div class="page-heading"><div><div class="eyebrow">IT ASSET OPERATIONS</div>'
                f'<h1>{heading}</h1><p class="auth-help">{intro}</p></div></div>'
                f'{notice}<section class="panel form-panel"><form class="form-grid" method="post" action="{path}">'
                f'{fields}<div class="form-actions"><span>M&#7853;t kh&#7849;u &#273;&#432;&#7907;c b&#7843;o v&#7879; an to&#224;n khi l&#432;u.</span>'
                '<button class="button primary" type="submit">Ti&#7871;p t&#7909;c</button></div></form></section>'
            )
            self._send(
                status,
                _shell(title, content, "system", auth=True).encode("utf-8"),
                "text/html; charset=utf-8",
            )

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
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
                "font-src https://fonts.gstatic.com; form-action 'self'; frame-ancestors 'none'",
            )
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
    database = Database.from_env(ROOT.parent / ".env")
    try:
        database.initialize()
    except (RuntimeError, ValueError) as error:
        parser.exit(1, f"Lỗi khởi tạo database: {error}\n")
    server = ThreadingHTTPServer(
        (args.host, args.port), make_handler(build_controller(database))
    )
    print(f"ITmanager đang chạy tại http://{args.host}:{args.port} (Ctrl+C để dừng)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng ITmanager...")
    finally:
        server.server_close()
        database.close()


def _parse_multipart_form(
    body: bytes, content_type: str
) -> tuple[dict[str, str], list[Path]]:
    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("ascii") + body
    )
    if not message.is_multipart():
        raise ValueError("Biểu mẫu tải tệp không hợp lệ.")
    fields: dict[str, str] = {}
    paths: list[Path] = []
    total_file_bytes = 0
    upload_root = ROOT / "uploads"
    upload_root.mkdir(exist_ok=True)
    try:
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            if filename:
                if len(payload) > MAX_UPLOAD_BYTES:
                    raise ValueError("Tệp tải lên vượt quá giới hạn 5 MB.")
                total_file_bytes += len(payload)
                if total_file_bytes > MAX_UPLOAD_BYTES:
                    raise ValueError("Tổng dung lượng tệp vượt quá giới hạn 5 MB.")
                safe_name = Path(filename.replace("\\", "/")).name
                safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name).strip("._")
                extension = Path(safe_name).suffix.lower()
                if not safe_name or extension not in ALLOWED_UPLOAD_EXTENSIONS:
                    raise ValueError("Định dạng tệp không được hỗ trợ.")
                stored_name = f"{uuid.uuid4().hex}_{safe_name}"
                destination = upload_root / stored_name
                destination.write_bytes(payload)
                paths.append(destination)
                fields["attachments"] = "\n".join(
                    filter(None, (fields.get("attachments", ""), f"uploads/{stored_name}"))
                )
            else:
                charset = part.get_content_charset() or "utf-8"
                fields[name] = payload.decode(charset)
    except (LookupError, UnicodeDecodeError, OSError):
        for path in paths:
            path.unlink(missing_ok=True)
        raise ValueError("Không thể đọc hoặc lưu nội dung biểu mẫu/tệp tải lên.")
    except ValueError:
        for path in paths:
            path.unlink(missing_ok=True)
        raise
    return fields, paths


if __name__ == "__main__":
    main()

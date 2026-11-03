from collections.abc import Sequence
from html import escape
from urllib.parse import quote

from modules.asset_management.models import Asset
from modules.maintenance.models import MaintenanceTicket


MODULES = (
    ("dashboard", "Tổng quan", "/"),
    ("assets", "Tài sản", "/assets"),
    ("assignment", "Cấp phát", "/assignment"),
    ("maintenance", "Bảo trì", "/maintenance"),
    ("inventory", "Kiểm kê", "/inventory"),
    ("software", "Phần mềm & license", "/software"),
    ("employees", "Nhân viên", "/employees"),
    ("reports", "Báo cáo", "/reports"),
    ("system", "Hệ thống", "/system"),
)


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _badge(value: str) -> str:
    return f'<span class="badge">{_e(value)}</span>'


def _shell(title: str, content: str, active: str, notice: str = "") -> str:
    navigation = "".join(
        f'<a class="nav-link{" active" if key == active else ""}" href="{path}">'
        f'<span class="nav-icon">{icon}</span>{label}</a>'
        for key, label, path, icon in (
            ("dashboard", "Tổng quan", "/", "⌂"),
            ("assets", "Tài sản", "/assets", "▣"),
            ("assignment", "Cấp phát", "/assignment", "⇄"),
            ("maintenance", "Bảo trì", "/maintenance", "⚙"),
            ("inventory", "Kiểm kê", "/inventory", "▤"),
            ("software", "Phần mềm & license", "/software", "◈"),
            ("employees", "Nhân viên", "/employees", "♙"),
            ("reports", "Báo cáo", "/reports", "▥"),
            ("system", "Hệ thống", "/system", "⚑"),
        )
    )
    banner = f'<div class="notice">{_e(notice)}</div>' if notice else ""
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f5f7fb">
  <title>{_e(title)} · ITmanager</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <aside class="sidebar">
    <a class="brand" href="/"><span class="brand-mark">IT</span>
      <span>ITmanager<small>ASSET OPERATIONS</small></span></a>
    <div class="nav-caption">WORKSPACE</div>
    <nav>{navigation}</nav>
    <div class="sidebar-footer"><span class="status-dot"></span> Hệ thống sẵn sàng</div>
  </aside>
  <main class="main">
    <header class="topbar"><div class="breadcrumbs">Không gian làm việc <span>/</span>
      <strong>{_e(title)}</strong></div><div class="profile"><span class="avatar">IT</span>
      <span>Quản trị viên<small>IT Operations</small></span></div></header>
    <section class="page">{banner}{content}
      <footer>ITmanager <span>·</span> Quản lý vận hành tài sản</footer>
    </section>
  </main>
</body>
</html>"""


def dashboard(assets: Sequence[Asset], tickets: Sequence[MaintenanceTicket]) -> str:
    in_use = sum(asset.status.value == "Đang dùng" for asset in assets)
    maintenance = sum(ticket.completed_on is None for ticket in tickets)
    recent_assets = "".join(
        f"""<tr><td><span class="asset-id">{_e(asset.asset_code)}</span></td>
        <td><strong>{_e(asset.model)}</strong><small>{_e(asset.manufacturer)}</small></td>
        <td>{_e(asset.category)}</td><td>{_e(asset.location)}</td>
        <td>{_badge(asset.status.value)}</td></tr>"""
        for asset in assets[:5]
    ) or '<tr><td class="empty" colspan="5">Chưa có tài sản. Thêm thiết bị đầu tiên để bắt đầu.</td></tr>'
    open_tickets = "".join(
        f'<li><span class="timeline-dot"></span><div><strong>{_e(ticket.ticket_id)} · '
        f'{_e(ticket.asset_code)}</strong><small>{_e(ticket.issue_description)}</small></div>'
        f'<span class="muted">{_e(ticket.received_on)}</span></li>'
        for ticket in tickets if ticket.completed_on is None
    ) or '<li class="empty">Không có phiếu bảo trì đang mở.</li>'
    content = f"""
      <div class="page-heading"><div><div class="eyebrow">OVERVIEW</div>
        <h1>Tổng quan</h1><p>Theo dõi tài sản và hoạt động IT của bạn.</p></div>
        <a class="button primary" href="/assets#asset-form">＋ Thêm tài sản</a></div>
      <div class="stats">
        <article class="stat-card"><div class="stat-icon blue">▣</div><div class="stat-label">Tổng tài sản</div>
          <div class="stat-value">{len(assets)}</div><div class="stat-hint">Thiết bị trong hệ thống</div></article>
        <article class="stat-card"><div class="stat-icon green">✓</div><div class="stat-label">Đang sử dụng</div>
          <div class="stat-value">{in_use}</div><div class="stat-hint">Tài sản đang được dùng</div></article>
        <article class="stat-card"><div class="stat-icon amber">⚙</div><div class="stat-label">Phiếu bảo trì mở</div>
          <div class="stat-value">{maintenance}</div><div class="stat-hint">Cần theo dõi xử lý</div></article>
        <article class="stat-card"><div class="stat-icon violet">◈</div><div class="stat-label">Module nghiệp vụ</div>
          <div class="stat-value">08</div><div class="stat-hint">Quản lý tập trung</div></article>
      </div>
      <div class="content-grid">
        <section class="panel"><div class="panel-heading"><div><h2>Tài sản gần đây</h2>
          <p>Danh sách thiết bị mới nhất</p></div><a class="text-link" href="/assets">Xem tất cả →</a></div>
          <div class="table-wrap"><table><thead><tr><th>Mã tài sản</th><th>Thiết bị</th>
          <th>Loại</th><th>Vị trí</th><th>Tình trạng</th></tr></thead><tbody>{recent_assets}</tbody></table></div>
        </section>
        <section class="panel activity"><div class="panel-heading"><div><h2>Bảo trì cần chú ý</h2>
          <p>Theo dõi các phiếu đang mở</p></div><a class="text-link" href="/maintenance">Tất cả →</a></div>
          <ul class="timeline">{open_tickets}</ul>
        </section>
      </div>
      <section class="welcome"><div><div class="eyebrow">IT ASSET MANAGEMENT</div>
        <h2>Mọi tài sản. Một nơi quản lý.</h2><p>Quản lý vòng đời thiết bị, hoạt động bảo trì
        và vận hành IT trên cùng một nền tảng.</p></div><span class="welcome-art">▦</span></section>"""
    return _shell("Tổng quan", content, "dashboard")


def asset_page(assets: Sequence[Asset], query: str = "", notice: str = "") -> str:
    query_folded = query.casefold()
    filtered = [
        asset for asset in assets
        if query_folded in " ".join(
            (asset.asset_code, asset.serial_number, asset.model, asset.manufacturer, asset.category)
        ).casefold()
    ]
    rows = "".join(
        f"""<tr><td><span class="asset-id">{_e(asset.asset_code)}</span>
        <small>SN: {_e(asset.serial_number)}</small></td>
        <td><strong>{_e(asset.model)}</strong><small>{_e(asset.manufacturer)}</small></td>
        <td>{_e(asset.category)}</td><td>{_e(asset.location)}</td>
        <td>{_badge(asset.status.value)}</td>
        <td>{_e(f"{asset.value:,.0f} ₫")}</td>
        <td><details class="detail"><summary>Chi tiết</summary><div class="detail-popover">
        <strong>{_e(asset.asset_code)}</strong><span>Ngày mua: {_e(asset.purchase_date)}</span>
        <span>Bảo hành: {_e(asset.warranty_until or "Không có")}</span>
        <span>Lịch sử thay đổi: {len(asset.history)} mục</span>
        <span>Tệp đính kèm: {len(asset.attachments)} mục</span></div></details></td></tr>"""
        for asset in filtered
    ) or '<tr><td class="empty" colspan="7">Không tìm thấy tài sản phù hợp.</td></tr>'
    content = f"""
      <div class="page-heading"><div><div class="eyebrow">ASSET MANAGEMENT</div><h1>Tài sản</h1>
      <p>Quản lý tập trung thông tin và tình trạng thiết bị.</p></div>
      <a class="button primary" href="#asset-form">＋ Thêm tài sản</a></div>
      <section class="panel"><div class="toolbar"><form class="search" method="get" action="/assets">
        <span>⌕</span><input name="q" value="{_e(query)}" placeholder="Tìm mã tài sản, serial, model...">
        <button class="button secondary" type="submit">Tìm kiếm</button></form>
        <span class="result-count">{len(filtered)} tài sản</span></div>
        <div class="table-wrap"><table><thead><tr><th>Mã / Serial</th><th>Thiết bị / Hãng</th>
        <th>Phân loại</th><th>Vị trí</th><th>Tình trạng</th><th>Giá trị</th><th></th></tr></thead>
        <tbody>{rows}</tbody></table></div></section>
      <section class="panel form-panel" id="asset-form"><div class="panel-heading"><div>
        <h2>Thêm tài sản mới</h2><p>Nhập thông tin thiết bị vào hệ thống</p></div></div>
        <form class="form-grid" method="post" action="/assets">
          <label>Mã tài sản <span>*</span><input name="asset_code" required placeholder="VD: IT-001"></label>
          <label>Serial Number<input name="serial_number" placeholder="VD: SN-0001"></label>
          <label>Model <span>*</span><input name="model" required placeholder="Tên model thiết bị"></label>
          <label>Hãng sản xuất<input name="manufacturer" placeholder="VD: Dell"></label>
          <label>Loại thiết bị <span>*</span><select name="category" required>
            <option>Máy tính</option><option>Máy in</option><option>Thiết bị mạng</option>
            <option>Máy công nghiệp</option><option>Tablet</option><option>Phụ kiện</option>
          </select></label>
          <label>Vị trí <span>*</span><input name="location" required placeholder="VD: Văn phòng tầng 1"></label>
          <label>Ngày mua<input name="purchase_date" type="date"></label>
          <label>Giá trị (VND)<input name="value" type="number" min="0" step="1000" value="0"></label>
          <label>Hạn bảo hành<input name="warranty_until" type="date"></label>
          <label>Tình trạng<select name="status"><option>Sẵn sàng</option><option>Đang dùng</option>
            <option>Đang sửa</option><option>Thanh lý</option></select></label>
          <div class="form-actions"><span><span>*</span> Trường bắt buộc</span>
            <button class="button primary" type="submit">Lưu tài sản</button></div>
        </form></section>"""
    return _shell("Tài sản", content, "assets", notice)


def maintenance_page(
    tickets: Sequence[MaintenanceTicket], assets: Sequence[Asset], notice: str = ""
) -> str:
    open_count = sum(ticket.completed_on is None for ticket in tickets)
    total_cost = sum((ticket.cost for ticket in tickets), start=0)
    rows = "".join(
        f"""<tr><td><span class="asset-id">{_e(ticket.ticket_id)}</span></td>
        <td><strong>{_e(ticket.asset_code)}</strong><small>{_e(ticket.issue_description)}</small></td>
        <td>{_badge(ticket.maintenance_type.value)}</td><td>{_e(ticket.received_on)}</td>
        <td>{_e(ticket.handler)}</td><td>{_e(f"{ticket.cost:,.0f} ₫")}</td>
        <td>{_badge("Hoàn thành" if ticket.completed_on else "Đang xử lý")}
        {f'<small>Ngày xong: {_e(ticket.completed_on)}</small>' if ticket.completed_on else
        f'<form class="inline-form" method="post" action="/maintenance/{quote(ticket.ticket_id, safe="")}/complete">'
        f'<button class="text-button" type="submit">Đánh dấu hoàn thành</button></form>'}</td></tr>"""
        for ticket in tickets
    ) or '<tr><td class="empty" colspan="7">Chưa có phiếu bảo trì. Tạo phiếu mới để bắt đầu theo dõi.</td></tr>'
    asset_options = "".join(
        f'<option value="{_e(asset.asset_code)}">{_e(asset.asset_code)} · {_e(asset.model)}</option>'
        for asset in assets
    )
    content = f"""
      <div class="page-heading"><div><div class="eyebrow">MAINTENANCE</div><h1>Bảo trì & sửa chữa</h1>
      <p>Theo dõi phiếu xử lý kỹ thuật và lịch sử sửa chữa thiết bị.</p></div>
      <a class="button primary" href="#ticket-form">＋ Tạo phiếu mới</a></div>
      <div class="stats compact">
        <article class="stat-card"><div class="stat-label">Tổng phiếu</div><div class="stat-value">{len(tickets)}</div>
          <div class="stat-hint">Phiếu bảo trì & sửa chữa</div></article>
        <article class="stat-card"><div class="stat-label">Đang xử lý</div><div class="stat-value">{open_count}</div>
          <div class="stat-hint">Chưa hoàn thành</div></article>
        <article class="stat-card"><div class="stat-label">Tổng chi phí</div><div class="stat-value money">
          {_e(f"{total_cost:,.0f}")} <small>₫</small></div><div class="stat-hint">Tổng chi phí đã ghi nhận</div></article>
      </div>
      <section class="panel"><div class="panel-heading"><div><h2>Lịch sử bảo trì</h2>
        <p>Toàn bộ phiếu bảo trì và sửa chữa thiết bị</p></div></div>
        <div class="table-wrap"><table><thead><tr><th>Mã phiếu</th><th>Thiết bị / Mô tả lỗi</th>
        <th>Loại</th><th>Ngày nhận</th><th>Người xử lý</th><th>Chi phí</th><th>Trạng thái</th>
        </tr></thead><tbody>{rows}</tbody></table></div></section>
      <section class="panel form-panel" id="ticket-form"><div class="panel-heading"><div>
        <h2>Tạo phiếu bảo trì / sửa chữa</h2><p>Ghi nhận tiếp nhận thiết bị và nội dung xử lý</p></div></div>
        <form class="form-grid" method="post" action="/maintenance">
          <label>Mã phiếu <span>*</span><input name="ticket_id" required placeholder="VD: MT-001"></label>
          <label>Thiết bị <span>*</span><select name="asset_code" required>
            <option value="">Chọn thiết bị</option>{asset_options}</select></label>
          <label>Phân loại <span>*</span><select name="maintenance_type">
            <option value="repair">Sửa chữa đột xuất</option>
            <option value="scheduled">Bảo trì định kỳ</option></select></label>
          <label>Ngày tiếp nhận <span>*</span><input name="received_on" type="date" required></label>
          <label>Người xử lý <span>*</span><input name="handler" required placeholder="Tên kỹ thuật viên"></label>
          <label>Chi phí (VND)<input name="cost" type="number" min="0" step="1000" value="0"></label>
          <label class="full-width">Mô tả lỗi / Nội dung bảo trì <span>*</span>
            <textarea name="issue_description" required rows="3" placeholder="Mô tả tình trạng thiết bị..."></textarea></label>
          <label class="full-width">Linh kiện thay thế
            <input name="replacement_parts" placeholder="Phân tách bằng dấu phẩy"></label>
          <div class="form-actions"><span><span>*</span> Trường bắt buộc</span>
            <button class="button primary" type="submit">Tạo phiếu</button></div>
        </form></section>"""
    return _shell("Bảo trì", content, "maintenance", notice)


def module_placeholder(module_key: str) -> str:
    module = next(item for item in MODULES if item[0] == module_key)
    _, title, path = module
    descriptions = {
        "assignment": "Cấp phát thiết bị, thu hồi và theo dõi lịch sử bàn giao.",
        "inventory": "Tạo đợt kiểm kê và đối chiếu tài sản theo khu vực.",
        "software": "Quản lý danh mục phần mềm, license và thời hạn sử dụng.",
        "employees": "Danh sách nhân viên và tài khoản người dùng hệ thống.",
        "reports": "Tổng hợp tài sản, chi phí và các mốc cần chú ý.",
        "system": "Cấu hình danh mục, phân quyền và nhật ký hoạt động.",
    }
    content = f"""
      <div class="page-heading"><div><div class="eyebrow">ITMANAGER MODULE</div>
      <h1>{_e(title)}</h1><p>{_e(descriptions[module_key])}</p></div></div>
      <section class="panel coming-soon"><div class="coming-icon">◈</div>
        <div class="eyebrow">MODULE FOUNDATION</div><h2>Màn hình đang được hoàn thiện</h2>
        <p>Cấu trúc Model–View–Controller cho module này đã sẵn sàng. Nghiệp vụ web và
        lưu trữ dữ liệu chưa được triển khai.</p><a class="button secondary" href="/">← Về tổng quan</a>
      </section>"""
    return _shell(title, content, module_key)

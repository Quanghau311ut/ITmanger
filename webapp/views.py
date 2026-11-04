from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from html import escape
from urllib.parse import quote
from urllib.parse import quote

from modules.asset_management.models import Asset, AssetStatus
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


NAV_ICONS = {
    "dashboard": "&#8962;",
    "assets": "&#9635;",
    "assignment": "&#8644;",
    "maintenance": "&#9881;",
    "inventory": "&#9636;",
    "software": "&#9672;",
    "employees": "&#9817;",
    "reports": "&#9637;",
    "system": "&#9873;",
}


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _badge(value: str) -> str:
    return f'<span class="badge">{_e(value)}</span>'


def _attachment_links(paths: Sequence[str]) -> str:
    links = []
    for path in paths:
        if path.startswith("uploads/") and ".." not in path.split("/"):
            safe_path = quote(path, safe="/")
            links.append(
                f'<a class="text-link" href="/{safe_path}" target="_blank" rel="noopener">'
                f'{_e(path.rsplit("/", 1)[-1])}</a>'
            )
    return "".join(links)


def _shell(
    title: str, content: str, active: str, notice: str = "", auth: bool = False
) -> str:
    navigation = "".join(
        f'<a class="nav-link{" active" if key == active else ""}" href="{path}">'
        f'<span class="nav-icon">{NAV_ICONS[key]}</span>{label}</a>'
        for key, label, path in MODULES
    )
    banner = f'<div class="notice">{_e(notice)}</div>' if notice else ""
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f5f7fb">
  <title>{_e(title)} · ITmanager</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css">
</head>
<body{" class=\"auth-page\"" if auth else ""}>
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
      <footer class="site-footer">
        <a class="company-link" href="https://www.quanganh.com" target="_blank" rel="noopener noreferrer">
          Công ty Cổ phần sản xuất Thương mại dịch vụ Quang Anh
        </a>
      </footer>
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


def asset_page(
    assets: Sequence[Asset],
    query: str = "",
    notice: str = "",
    category_values: Sequence[str] = (),
    location_values: Sequence[str] = (),
) -> str:
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
        <td><details class="detail"><summary>Chi tiết / sửa</summary><div class="detail-popover asset-editor">
        <strong>{_e(asset.asset_code)} · {len(asset.history)} thay đổi</strong>
        {_attachment_links(asset.attachments)}
        <form method="post" enctype="multipart/form-data" action="/assets/{quote(asset.asset_code, safe="")}/update">
        <label>Serial<input name="serial_number" value="{_e(asset.serial_number)}"></label>
        <label>Model<input name="model" required value="{_e(asset.model)}"></label>
        <label>Hãng<input name="manufacturer" value="{_e(asset.manufacturer)}"></label>
        <label>Loại<input name="category" required value="{_e(asset.category)}"></label>
        <label>Vị trí<input name="location" required value="{_e(asset.location)}"></label>
        <label>Ngày mua<input name="purchase_date" type="date" value="{_e(asset.purchase_date)}"></label>
        <label>Giá trị<input name="value" type="number" min="0" step="1000" value="{_e(asset.value)}"></label>
        <label>Bảo hành<input name="warranty_until" type="date" value="{_e(asset.warranty_until or "")}"></label>
        <label>Tình trạng<select name="status">{''.join(f'<option value="{_e(status.value)}" {"selected" if status == asset.status else ""}>{_e(status.value)}</option>' for status in AssetStatus)}</select></label>
        <label>Tệp đính kèm (đường dẫn, mỗi dòng một tệp)<textarea name="attachments" rows="2">{_e(chr(10).join(asset.attachments))}</textarea></label>
        <label>Tải ảnh / chứng từ<input type="file" name="files" multiple accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.txt"></label>
        <button class="button primary">Lưu chỉnh sửa</button></form>
        <form method="post" action="/assets/{quote(asset.asset_code, safe="")}/retire">
        <button class="button secondary" {"disabled" if asset.status.value == "Thanh lý" else ""}>Đánh dấu thanh lý</button></form>
        </div></details></td></tr>"""
        for asset in filtered
    ) or '<tr><td class="empty" colspan="7">Không tìm thấy tài sản phù hợp.</td></tr>'
    categories = category_values or (
        "Máy tính", "Máy in", "Thiết bị mạng", "Máy công nghiệp", "Tablet", "Phụ kiện"
    )
    category_options = "".join(f"<option>{_e(item)}</option>" for item in categories)
    location_list = "".join(f'<option value="{_e(item)}">' for item in location_values)
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
        <form class="form-grid" method="post" enctype="multipart/form-data" action="/assets">
          <label>Mã tài sản <span>*</span><input name="asset_code" required placeholder="VD: IT-001"></label>
          <label>Serial Number<input name="serial_number" placeholder="VD: SN-0001"></label>
          <label>Model <span>*</span><input name="model" required placeholder="Tên model thiết bị"></label>
          <label>Hãng sản xuất<input name="manufacturer" placeholder="VD: Dell"></label>
          <label>Loại thiết bị <span>*</span><select name="category" required>{category_options}</select></label>
          <label>Vị trí <span>*</span><input name="location" list="asset-locations" required placeholder="VD: Văn phòng tầng 1">
            <datalist id="asset-locations">{location_list}</datalist></label>
          <label>Ngày mua<input name="purchase_date" type="date"></label>
          <label>Giá trị (VND)<input name="value" type="number" min="0" step="1000" value="0"></label>
          <label>Hạn bảo hành<input name="warranty_until" type="date"></label>
          <label class="full-width">Tệp đính kèm (đường dẫn, mỗi dòng một tệp)
            <textarea name="attachments" rows="2" placeholder="docs/hoa-don.pdf"></textarea></label>
          <label class="full-width">Tải ảnh / chứng từ<input type="file" name="files" multiple
            accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.txt"></label>
          <label>Tình trạng<select name="status"><option>Sẵn sàng</option><option>Đang dùng</option>
            <option>Đang sửa</option><option>Thanh lý</option></select></label>
          <div class="form-actions"><span><span>*</span> Trường bắt buộc</span>
            <button class="button primary" type="submit">Lưu tài sản</button></div>
        </form></section>"""
    return _shell("Tài sản", content, "assets", notice)


def maintenance_page(
    tickets: Sequence[MaintenanceTicket],
    assets: Sequence[Asset],
    notice: str = "",
    schedules: Sequence[dict[str, object]] = (),
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
    schedule_options = "".join(
        f'<option value="{_e(asset.asset_code)}">{_e(asset.asset_code)} · {_e(asset.model)}</option>'
        for asset in assets
    )
    schedule_rows = "".join(
        f'<tr><td>{_e(item["asset_code"])}</td><td>{_e(item["asset_model"])}</td>'
        f'<td>{_e(item["due_on"])}</td><td>{item["interval_days"]} ngày</td>'
        f'<td>{_e(item["notes"])}</td></tr>'
        for item in schedules
    ) or '<tr><td class="empty" colspan="5">Chưa lập lịch bảo trì định kỳ.</td></tr>'
    due_schedules = sum(
        (item["due_on"] - date.today()).days <= 30 for item in schedules
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
      <section class="panel"><div class="panel-heading"><div><h2>Lịch bảo trì định kỳ</h2>
        <p>{due_schedules} thiết bị đến hạn trong 30 ngày</p></div></div>
        <div class="table-wrap"><table><thead><tr><th>Tài sản</th><th>Thiết bị</th><th>Đến hạn</th>
        <th>Chu kỳ</th><th>Ghi chú</th></tr></thead><tbody>{schedule_rows}</tbody></table></div></section>
      <section class="panel form-panel"><div class="panel-heading"><div><h2>Lập lịch bảo trì</h2></div></div>
        <form class="form-grid" method="post" action="/maintenance/schedule">
        <label>Tài sản<select name="asset_code" required><option value="">Chọn thiết bị</option>{schedule_options}</select></label>
        <label>Ngày đến hạn<input type="date" name="due_on" required></label>
        <label>Chu kỳ (ngày)<input type="number" name="interval_days" min="1" value="180" required></label>
        <label>Ghi chú<input name="notes"></label><div class="form-actions"><span>Bảo trì định kỳ</span>
        <button class="button primary">Lưu lịch</button></div></form></section>
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


def workflow_page(
    module_key: str,
    data: dict[str, object],
    notice: str = "",
) -> str:
    if module_key == "assignment":
        return _assignment_page(data, notice)
    if module_key == "inventory":
        return _inventory_page(data, notice)
    if module_key == "software":
        return _software_page(data, notice)
    if module_key == "employees":
        return _employee_page(data, notice)
    if module_key == "reports":
        return _report_page(data)
    if module_key == "system":
        return _system_page(data, notice)
    raise ValueError(f"Unknown module: {module_key}")


def _assignment_page(data: dict[str, object], notice: str) -> str:
    employees = data["employees"]
    assets = data["assets"]
    assignments = data["assignments"]
    employee_options = "".join(
        f'<option value="{_e(row["employee_id"])}">{_e(row["employee_id"])} · '
        f'{_e(row["full_name"])}</option>'
        for row in employees if row["status"] == "Đang làm"
    )
    asset_options = "".join(
        f'<option value="{_e(asset.asset_code)}">{_e(asset.asset_code)} · '
        f'{_e(asset.model)}</option>'
        for asset in assets if asset.status.value == "Sẵn sàng"
    )
    rows = "".join(
        f'<tr><td><strong>{_e(item["assignment_id"])}</strong></td>'
        f'<td>{_e(item["asset_code"])}<small>{_e(item["asset_model"])}</small></td>'
        f'<td>{_e(item["employee_name"])}<small>{_e(item["employee_id"])}</small></td>'
        f'<td>{_e(item["issued_on"])}</td><td>{_e(item["due_on"] or "—")}</td>'
        f'<td>{_badge(str(item["status"]))}'
        f'{_return_form(item) if item["status"] == "Đang cấp phát" else ""}</td></tr>'
        for item in assignments
    ) or '<tr><td class="empty" colspan="6">Chưa có lịch sử cấp phát.</td></tr>'
    overdue = sum(
        item["status"] == "Đang cấp phát" and item["due_on"] and item["due_on"] < date.today()
        for item in assignments
    )
    separated = sum(
        item["status"] == "Đang cấp phát"
        and next((row["status"] for row in employees if row["employee_id"] == item["employee_id"]), "")
        == "Đã nghỉ"
        for item in assignments
    )
    content = f"""
    <div class="page-heading"><div><div class="eyebrow">ASSIGNMENT</div><h1>Cấp phát & thu hồi</h1>
    <p>Theo dõi bàn giao thiết bị, tình trạng thu hồi và các trường hợp quá hạn.</p></div></div>
    <div class="stats compact"><article class="stat-card"><div class="stat-label">Đang cấp phát</div>
    <div class="stat-value">{sum(item["status"] == "Đang cấp phát" for item in assignments)}</div></article>
    <article class="stat-card"><div class="stat-label">Quá hạn thu hồi</div><div class="stat-value">{overdue}</div></article>
    <article class="stat-card"><div class="stat-label">Nhân viên đã nghỉ</div><div class="stat-value">{separated}</div></article></div>
    <section class="panel"><div class="panel-heading"><div><h2>Lịch sử bàn giao</h2>
    <p>Các phiếu cấp phát đang mở và đã hoàn tất</p></div>
    <a class="button secondary" href="/assignments/print">In biên bản</a></div>
    <div class="table-wrap"><table><thead><tr><th>Mã phiếu</th><th>Tài sản</th><th>Người nhận</th>
    <th>Ngày cấp</th><th>Hạn thu hồi</th><th>Trạng thái / thao tác</th></tr></thead><tbody>{rows}</tbody></table></div></section>
    <section class="panel form-panel" id="assignment-form"><div class="panel-heading"><div><h2>Cấp phát thiết bị</h2>
    <p>Chỉ thiết bị sẵn sàng và nhân viên đang làm được chọn</p></div></div>
    <form class="form-grid" method="post" action="/assignment">
    <label>Mã phiếu <span>*</span><input name="assignment_id" required placeholder="AS-001"></label>
    <label>Tài sản <span>*</span><select name="asset_code" required><option value="">Chọn thiết bị</option>{asset_options}</select></label>
    <label>Nhân viên <span>*</span><select name="employee_id" required><option value="">Chọn người nhận</option>{employee_options}</select></label>
    <label>Ngày cấp <span>*</span><input type="date" name="issued_on" required value="{date.today().isoformat()}"></label>
    <label>Hạn thu hồi<input type="date" name="due_on"></label>
    <div class="form-actions"><span>Biên bản có thể in từ danh sách</span><button class="button primary">Lưu cấp phát</button></div>
    </form></section>"""
    return _shell("Cấp phát", content, "assignment", notice)


def _return_form(item: dict[str, object]) -> str:
    return (
        f'<details class="detail"><summary>Thu hồi</summary><form class="detail-popover" '
        f'method="post" action="/assignment/{quote(str(item["assignment_id"]), safe="")}/return">'
        '<label>Tình trạng khi thu về<textarea name="condition" required rows="2"></textarea></label>'
        f'<button class="button primary" name="returned_on" value="{date.today().isoformat()}">'
        'Xác nhận thu hồi</button></form></details>'
    )


def _inventory_page(data: dict[str, object], notice: str) -> str:
    assets = data["assets"]
    runs = data["runs"]
    categories = sorted({asset.category for asset in assets})
    locations = sorted({asset.location for asset in assets})
    rows = []
    for run in runs:
        discrepancies = "".join(
            f'<tr><td>{_e(item["asset_code"])}</td><td>{_badge(item["type"])}</td>'
            f'<td>{_e(item["expected"] or "—")}</td><td>{_e(item["actual"] or "—")}</td></tr>'
            for item in run["discrepancies"]
        ) or '<tr><td class="empty" colspan="4">Không có chênh lệch hiện tại.</td></tr>'
        rows.append(
            f'<section class="panel"><div class="panel-heading"><div><h2>{_e(run["run_id"])} · '
            f'{_e(run["scope"])}</h2><p>{_e(run["created_on"])} · Đã quét '
            f'{run["scanned_count"]}/{run["expected_count"]}</p></div>'
            f'<a class="button secondary" href="/inventory/export/{quote(str(run["run_id"]), safe="")}.csv">Xuất chênh lệch</a></div>'
            f'<form class="toolbar" method="post" action="/inventory/{quote(str(run["run_id"]), safe="")}/scan">'
            '<input name="asset_code" required placeholder="Quét / nhập mã tài sản">'
            '<input name="actual_location" required placeholder="Vị trí thực tế">'
            '<button class="button primary">Ghi nhận</button></form>'
            f'<div class="table-wrap"><table><thead><tr><th>Mã tài sản</th><th>Chênh lệch</th>'
            f'<th>Vị trí hệ thống</th><th>Vị trí thực tế</th></tr></thead><tbody>{discrepancies}</tbody></table></div></section>'
        )
    category_options = "".join(f'<option>{_e(item)}</option>' for item in categories)
    location_options = "".join(f'<option>{_e(item)}</option>' for item in locations)
    content = f"""
    <div class="page-heading"><div><div class="eyebrow">INVENTORY</div><h1>Kiểm kê tài sản</h1>
    <p>Tạo đợt kiểm kê, ghi nhận quét mã và theo dõi chênh lệch.</p></div></div>
    <section class="panel form-panel"><div class="panel-heading"><div><h2>Tạo đợt kiểm kê</h2>
    <p>Chụp danh sách tài sản tại thời điểm tạo đợt</p></div></div>
    <form class="form-grid" method="post" action="/inventory">
    <label>Mã đợt <span>*</span><input name="run_id" required placeholder="KK-2026-001"></label>
    <label>Ngày kiểm kê <input name="created_on" type="date" value="{date.today().isoformat()}"></label>
    <label>Phạm vi <select name="scope_type"><option value="all">Toàn công ty</option>
    <option value="category">Loại thiết bị</option><option value="location">Khu vực</option></select></label>
    <label>Giá trị loại / khu vực<input name="scope_value" list="inventory-scopes"
    placeholder="Để trống nếu chọn toàn công ty"><datalist id="inventory-scopes">{category_options}{location_options}</datalist></label>
    <div class="form-actions"><span>Chọn loại/khu vực thì chọn giá trị tương ứng</span><button class="button primary">Tạo đợt kiểm kê</button></div>
    </form></section>{''.join(rows) or '<section class="panel"><p class="empty">Chưa có đợt kiểm kê.</p></section>'}"""
    return _shell("Kiểm kê", content, "inventory", notice)


def _software_page(data: dict[str, object], notice: str) -> str:
    licenses = data["licenses"]
    assets = data["assets"]
    employees = data["employees"]
    rows = "".join(
        f'<tr><td><strong>{_e(item["software_name"])}</strong><small>{_e(item["license_id"])}</small></td>'
        f'<td>{_badge(str(item["license_type"]))}</td><td>{item["quantity"]}</td>'
        f'<td>{len(item["assignments"])}/{item["quantity"]}</td>'
        f'<td>{_e(item["expires_on"] or "Vĩnh viễn")}'
        f'{" " + _badge("Sắp hết hạn") if item["expires_on"] and 0 <= (item["expires_on"] - date.today()).days <= 30 else ""}</td></tr>'
        for item in licenses
    ) or '<tr><td class="empty" colspan="5">Chưa có license.</td></tr>'
    license_options = "".join(
        f'<option value="{_e(item["license_id"])}">{_e(item["software_name"])} · {_e(item["license_id"])}</option>'
        for item in licenses
    )
    subject_options = "".join(
        f'<option>{_e(row["employee_id"])}</option>' for row in employees
    ) + "".join(f'<option>{_e(asset.asset_code)}</option>' for asset in assets)
    install_rows = "".join(
        f'<tr><td>{_e(item["software_name"])}</td><td>{_e(item["asset_code"])} · '
        f'{_e(item["asset_model"])}</td><td>{_e(item["installed_on"])}</td></tr>'
        for item in data["installations"]
    ) or '<tr><td class="empty" colspan="3">Chưa ghi nhận phần mềm cài đặt.</td></tr>'
    allocation_rows = "".join(
        f'<tr><td>{_e(item["software_name"])}</td><td>{_e(subject)}</td><td>'
        f'<form method="post" action="/software/unassign"><input type="hidden" name="license_id" value="{_e(item["license_id"])}">'
        f'<input type="hidden" name="subject_id" value="{_e(subject)}"><button class="text-button">Thu hồi</button></form></td></tr>'
        for item in licenses for subject in item["assignments"]
    ) or '<tr><td class="empty" colspan="3">Chưa gán license.</td></tr>'
    content = f"""
    <div class="page-heading"><div><div class="eyebrow">SOFTWARE ASSET MANAGEMENT</div><h1>Phần mềm & license</h1>
    <p>Quản lý số lượng, thời hạn, phân bổ và phần mềm trên từng thiết bị.</p></div></div>
    <section class="panel"><div class="panel-heading"><div><h2>Danh mục license</h2>
    <p>Cảnh báo license hết hạn trong 30 ngày được đánh dấu</p></div></div>
    <div class="table-wrap"><table><thead><tr><th>Phần mềm</th><th>Loại</th><th>Số lượng</th><th>Đã gán</th><th>Hết hạn</th></tr></thead><tbody>{rows}</tbody></table></div></section>
    <section class="panel form-panel"><div class="panel-heading"><div><h2>Thêm / cập nhật license</h2></div></div>
    <form class="form-grid" method="post" action="/software/license">
    <label>Mã license <span>*</span><input name="license_id" required></label>
    <label>Tên phần mềm <span>*</span><input name="software_name" required></label>
    <label>Loại <select name="license_type"><option>Thuê bao</option><option>Vĩnh viễn</option></select></label>
    <label>Số lượng<input name="quantity" type="number" min="1" value="1" required></label>
    <label>Ngày hết hạn<input name="expires_on" type="date"></label>
    <div class="form-actions"><span>Để trống ngày nếu license vĩnh viễn</span><button class="button primary">Lưu license</button></div></form></section>
    <section class="panel form-panel"><div class="panel-heading"><div><h2>Gán license</h2></div></div>
    <form class="toolbar" method="post" action="/software/assign">
    <select name="license_id" required><option value="">Chọn license</option>{license_options}</select>
    <select name="subject_id" required><option value="">Người dùng / thiết bị</option>{subject_options}</select>
    <button class="button primary">Gán license</button></form></section>
    <section class="panel"><div class="panel-heading"><h2>License đã gán</h2></div>
    <div class="table-wrap"><table><thead><tr><th>Phần mềm</th><th>Người dùng / thiết bị</th><th></th></tr></thead><tbody>{allocation_rows}</tbody></table></div></section>
    <section class="panel form-panel"><div class="panel-heading"><div><h2>Ghi nhận cài đặt phần mềm</h2></div></div>
    <form class="toolbar" method="post" action="/software/install">
    <input name="software_name" required placeholder="Tên phần mềm"><select name="asset_code" required>
    <option value="">Chọn thiết bị</option>{''.join(f'<option value="{_e(a.asset_code)}">{_e(a.asset_code)} · {_e(a.model)}</option>' for a in assets)}</select>
    <input type="date" name="installed_on" value="{date.today().isoformat()}"><button class="button primary">Ghi nhận</button></form>
    <div class="table-wrap"><table><thead><tr><th>Phần mềm</th><th>Thiết bị</th><th>Ngày cài</th></tr></thead><tbody>{install_rows}</tbody></table></div></section>"""
    return _shell("Phần mềm & license", content, "software", notice)


def _employee_page(data: dict[str, object], notice: str) -> str:
    rows = "".join(
        f'<tr><td><strong>{_e(item["employee_id"])}</strong></td><td>{_e(item["full_name"])}</td>'
        f'<td>{_e(item["department"])}</td><td>{_e(item["position"])}</td>'
        f'<td>{_e(item["email"])}</td><td>{_badge(str(item["status"]))}</td></tr>'
        for item in data["employees"]
    ) or '<tr><td class="empty" colspan="6">Chưa có nhân viên.</td></tr>'
    content = f"""
    <div class="page-heading"><div><div class="eyebrow">PEOPLE & ACCESS</div><h1>Nhân viên</h1>
    <p>Danh bạ nhân viên dùng cho cấp phát thiết bị và quản trị tài khoản.</p></div></div>
    <section class="panel"><div class="table-wrap"><table><thead><tr><th>Mã NV</th><th>Họ tên</th>
    <th>Phòng ban</th><th>Chức vụ</th><th>Email</th><th>Trạng thái</th></tr></thead><tbody>{rows}</tbody></table></div></section>
    <section class="panel form-panel"><div class="panel-heading"><div><h2>Thêm / cập nhật nhân viên</h2>
    <p>Dùng lại mã nhân viên để cập nhật thông tin hoặc đánh dấu đã nghỉ</p></div></div>
    <form class="form-grid" method="post" action="/employees">
    <label>Mã nhân viên <span>*</span><input name="employee_id" required></label>
    <label>Họ tên <span>*</span><input name="full_name" required></label>
    <label>Phòng ban<input name="department"></label><label>Chức vụ<input name="position"></label>
    <label>Email <span>*</span><input name="email" type="email" required></label>
    <label>Trạng thái<select name="status"><option>Đang làm</option><option>Đã nghỉ</option></select></label>
    <div class="form-actions"><span>Nhân viên đã nghỉ không thể nhận cấp phát mới</span><button class="button primary">Lưu nhân viên</button></div></form></section>"""
    return _shell("Nhân viên", content, "employees", notice)


def _report_page(data: dict[str, object]) -> str:
    assets = data["assets"]
    maintenance = data["maintenance"]
    licenses = data["licenses"]
    assignments = data["assignments"]

    def summary_rows(field: str) -> str:
        counts: dict[str, int] = {}
        for asset in assets:
            label = str(asset[field])
            counts[label] = counts.get(label, 0) + 1
        return "".join(
            f"<tr><td>{_e(label)}</td><td>{count}</td></tr>"
            for label, count in sorted(counts.items())
        ) or '<tr><td class="empty" colspan="2">Chưa có dữ liệu.</td></tr>'

    expiring_licenses = [
        item for item in licenses
        if item["expires_on"] and 0 <= (item["expires_on"] - date.today()).days <= 30
    ]
    costs = sum((item["cost"] for item in maintenance), Decimal("0"))
    active = sum(item["status"] == "Đang cấp phát" for item in assignments)
    expiring_warranties = [
        item for item in assets
        if item["warranty_until"]
        and 0 <= (item["warranty_until"] - date.today()).days <= 30
    ]
    warranty_expired = [
        item for item in assets
        if item["warranty_until"] and item["warranty_until"] < date.today()
    ]
    monthly_costs: dict[str, Decimal] = {}
    for item in maintenance:
        month = item["received_on"].strftime("%Y-%m")
        monthly_costs[month] = monthly_costs.get(month, Decimal("0")) + item["cost"]
    cost_rows = "".join(
        f'<tr><td>{_e(month)}</td><td>{_e(f"{amount:,.0f}")} ₫</td></tr>'
        for month, amount in sorted(monthly_costs.items(), reverse=True)
    ) or '<tr><td class="empty" colspan="2">Chưa có chi phí bảo trì.</td></tr>'
    content = f"""
    <div class="page-heading"><div><div class="eyebrow">REPORTING</div><h1>Báo cáo & thống kê</h1>
    <p>Tổng hợp tồn kho, phân bổ, bảo trì và cảnh báo thời hạn.</p></div>
    <div><a class="button secondary" href="/reports/export/assets.csv">Tài sản CSV</a>
    <a class="button secondary" href="/reports/export/maintenance.csv">Bảo trì CSV</a>
    <a class="button primary" href="/reports/export/licenses.csv">License CSV</a></div></div>
    <div class="stats compact"><article class="stat-card"><div class="stat-label">Tổng tài sản</div><div class="stat-value">{len(assets)}</div></article>
    <article class="stat-card"><div class="stat-label">Đang cấp phát</div><div class="stat-value">{active}</div></article>
    <article class="stat-card"><div class="stat-label">Chi phí sửa chữa</div><div class="stat-value money">{_e(f"{costs:,.0f}")} <small>₫</small></div></article></div>
    <div class="content-grid"><section class="panel"><div class="panel-heading"><h2>Tài sản theo loại</h2></div>
    <table><thead><tr><th>Loại thiết bị</th><th>Số lượng</th></tr></thead><tbody>{summary_rows("category")}</tbody></table></section>
    <section class="panel"><div class="panel-heading"><h2>Tài sản theo tình trạng</h2></div>
    <table><thead><tr><th>Tình trạng</th><th>Số lượng</th></tr></thead><tbody>{summary_rows("status")}</tbody></table></section></div>
    <div class="content-grid"><section class="panel"><div class="panel-heading"><h2>Tài sản theo vị trí</h2></div>
    <table><thead><tr><th>Vị trí</th><th>Số lượng</th></tr></thead><tbody>{summary_rows("location")}</tbody></table></section>
    <section class="panel"><div class="panel-heading"><h2>Tài sản theo phòng ban nhận</h2></div>
    <table><thead><tr><th>Phòng ban</th><th>Số lượng</th></tr></thead><tbody>{summary_rows("department")}</tbody></table></section></div>
    <section class="panel"><div class="panel-heading"><div><h2>Chi phí bảo trì theo tháng</h2></div></div>
    <div class="table-wrap"><table><thead><tr><th>Tháng tiếp nhận</th><th>Chi phí</th></tr></thead><tbody>{cost_rows}</tbody></table></div></section>
    <section class="panel"><div class="panel-heading"><div><h2>Cảnh báo license</h2><p>Sắp hết hạn trong 30 ngày</p></div></div>
    <div class="table-wrap"><table><thead><tr><th>Mã license</th><th>Phần mềm</th><th>Ngày hết hạn</th></tr></thead><tbody>
    {''.join(f'<tr><td>{_e(i["license_id"])}</td><td>{_e(i["software_name"])}</td><td>{_e(i["expires_on"])}</td></tr>' for i in expiring_licenses) or '<tr><td class="empty" colspan="3">Không có license sắp hết hạn.</td></tr>'}</tbody></table></div></section>
    <section class="panel"><div class="panel-heading"><div><h2>Bảo hành sắp hết hạn</h2><p>Trong 30 ngày tới</p></div></div>
    <div class="table-wrap"><table><thead><tr><th>Mã tài sản</th><th>Thiết bị</th><th>Ngày hết hạn</th></tr></thead><tbody>
    {''.join(f'<tr><td>{_e(i["asset_code"])}</td><td>{_e(i["category"])}</td><td>{_e(i["warranty_until"])}</td></tr>' for i in expiring_warranties) or '<tr><td class="empty" colspan="3">Không có bảo hành sắp hết hạn.</td></tr>'}</tbody></table></div></section>
    <section class="panel"><div class="panel-heading"><div><h2>Bảo hành đã hết hạn</h2><p>{len(warranty_expired)} tài sản</p></div></div>
    <div class="table-wrap"><table><thead><tr><th>Mã tài sản</th><th>Thiết bị</th><th>Ngày hết hạn</th></tr></thead><tbody>
    {''.join(f'<tr><td>{_e(i["asset_code"])}</td><td>{_e(i["category"])}</td><td>{_e(i["warranty_until"])}</td></tr>' for i in warranty_expired) or '<tr><td class="empty" colspan="3">Không có bảo hành hết hạn.</td></tr>'}</tbody></table></div></section>"""
    return _shell("Báo cáo", content, "reports")


def _system_account_access(accounts: Sequence[dict[str, str]]) -> str:
    rows = "".join(
        f'<tr><td>{_e(account["username"])}</td><td>{_e(account["employee_id"])}</td>'
        f'<td><form class="toolbar" method="post" action="/system/accounts/access">'
        f'<input type="hidden" name="username" value="{_e(account["username"])}">'
        f'<select name="role">'
        f'<option value="Admin" {"selected" if account["role"] == "Admin" else ""}>Admin</option>'
        f'<option value="IT Staff" {"selected" if account["role"] == "IT Staff" else ""}>IT Staff</option>'
        f'<option value="Viewer" {"selected" if account["role"] == "Viewer" else ""}>Viewer</option>'
        f'</select><select name="enabled">'
        f'<option value="true" {"selected" if account["enabled"] == "Đang hoạt động" else ""}>Hoạt động</option>'
        f'<option value="false" {"selected" if account["enabled"] != "Đang hoạt động" else ""}>Đã khóa</option>'
        f'</select><button class="button secondary">Cập nhật</button></form></td></tr>'
        for account in accounts
    ) or '<tr><td class="empty" colspan="3">Chưa có tài khoản.</td></tr>'
    return (
        '<section class="panel"><div class="panel-heading"><div><h2>Phân quyền tài khoản</h2>'
        '<p>Đổi vai trò hoặc khóa/mở tài khoản.</p></div></div>'
        '<div class="table-wrap"><table><thead><tr><th>Tên đăng nhập</th><th>Mã nhân viên</th>'
        f'<th>Vai trò và trạng thái</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
    )


def _system_page(data: dict[str, object], notice: str) -> str:
    categories = "".join(
        f'<tr><td><strong>{_e(item["category"])}</strong></td>'
        f'<td>{_e(", ".join(item["values"]))}</td></tr>'
        for item in data["categories"]
    ) or '<tr><td class="empty" colspan="2">Chưa cấu hình danh mục.</td></tr>'
    logs = "".join(
        f'<tr><td>{_e(item["occurred_at"])}</td><td>{_e(item["actor"])}</td>'
        f'<td>{_e(item["action"])}</td><td>{_e(item["entity"])} · {_e(item["entity_id"])}</td></tr>'
        for item in data["audit"]
    ) or '<tr><td class="empty" colspan="4">Chưa có nhật ký hoạt động.</td></tr>'
    account_rows = "".join(
        f'<tr><td>{_e(item["username"])}</td><td>{_e(item["employee_id"])}</td>'
        f'<td>{_badge(item["role"])}</td><td>{_e(item["enabled"])}</td></tr>'
        for item in data["accounts"]
    ) or '<tr><td class="empty" colspan="4">Chưa có tài khoản.</td></tr>'
    employee_options = "".join(
        f'<option value="{_e(item["employee_id"])}">{_e(item["employee_id"])} · {_e(item["full_name"])}</option>'
        for item in data["employees"]
        if item["status"] == "Đang làm"
    )
    content = f"""
    <div class="page-heading"><div><div class="eyebrow">SYSTEM</div><h1>Hệ thống</h1>
    <p>Danh mục dùng chung và nhật ký hoạt động ứng dụng.</p></div></div>
    <section class="panel"><div class="panel-heading"><h2>Danh mục cấu hình</h2></div>
    <div class="table-wrap"><table><thead><tr><th>Danh mục</th><th>Giá trị</th></tr></thead><tbody>{categories}</tbody></table></div></section>
    <section class="panel form-panel"><div class="panel-heading"><div><h2>Cập nhật danh mục</h2>
    <p>Nhập danh sách giá trị, phân tách bằng dấu phẩy</p></div></div>
    <form class="toolbar" method="post" action="/system/categories">
    <input name="category" required placeholder="VD: Vị trí">
    <input name="values" required placeholder="Văn phòng, Kho, Xưởng">
    <button class="button primary">Lưu danh mục</button></form></section>
    <section class="panel"><div class="panel-heading"><div><h2>Tài khoản & phân quyền</h2>
    <p>Mật khẩu tối thiểu 12 ký tự, lưu bằng PBKDF2</p></div></div>
    <div class="table-wrap"><table><thead><tr><th>Tên đăng nhập</th><th>Mã nhân viên</th><th>Vai trò</th><th>Trạng thái</th></tr></thead><tbody>{account_rows}</tbody></table></div>
    <form class="form-grid" method="post" action="/system/accounts">
    <label>Tên đăng nhập<input name="username" required></label>
    <label>Nhân viên<select name="employee_id" required><option value="">Chọn nhân viên</option>{employee_options}</select></label>
    <label>Mật khẩu ban đầu<input type="password" name="password" minlength="12" required></label>
    <label>Vai trò<select name="role"><option>IT Staff</option><option>Viewer</option><option>Admin</option></select></label>
    <div class="form-actions"><span>Chỉ Admin mới tạo được tài khoản</span><button class="button primary">Tạo tài khoản</button></div></form></section>
    <section class="panel"><div class="panel-heading"><div><h2>Nhật ký hoạt động</h2>
    <p>200 hoạt động gần nhất</p></div></div>
    <div class="table-wrap"><table><thead><tr><th>Thời gian</th><th>Người thực hiện</th><th>Thao tác</th><th>Đối tượng</th></tr></thead><tbody>{logs}</tbody></table></div></section>"""
    content += _system_account_access(data["accounts"])
    return _shell("Hệ thống", content, "system", notice)

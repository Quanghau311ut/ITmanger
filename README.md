# ITmanager

Nền tảng Python theo MVC, chia thành 8 module nghiệp vụ:

| Thư mục | Phạm vi |
|---|---|
| `modules/asset_management/` | Hồ sơ tài sản, CRUD, tình trạng, tài liệu đính kèm và lịch sử thay đổi |
| `modules/assignment/` | Cấp phát, thu hồi, lịch sử và phát hiện cấp phát quá hạn |
| `modules/maintenance/` | Phiếu bảo trì/sửa chữa, chi phí, linh kiện và lịch sử theo tài sản |
| `modules/inventory/` | Đợt kiểm kê, ghi nhận quét mã và đối chiếu thừa/thiếu/sai vị trí |
| `modules/software_license/` | Danh mục license, số lượng, người/thiết bị được gán và cảnh báo hết hạn |
| `modules/employee/` | Nhân viên, tài khoản hệ thống và vai trò |
| `modules/reporting/` | Tổng hợp tài sản và chi phí sửa chữa |
| `modules/system/` | Phân quyền, cấu hình danh mục và audit log |

Mỗi module tách thành `models.py`, `controllers.py` và `views.py`. `main.py` là điểm khởi chạy; `tests/` chứa kiểm thử nghiệp vụ.

Chạy ứng dụng web (mặc định mở tại `http://127.0.0.1:8000`):

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Chỉnh .env theo SQL Server của bạn
python main.py
```

Có thể đổi cổng bằng `python main.py --port 8080`. Máy chủ mặc định chỉ lắng nghe trên `127.0.0.1`.

Chạy kiểm thử:

```powershell
python -m unittest discover -s tests
```

Ứng dụng kết nối SQL Server theo thông tin máy chủ `192.168.1.69` và database `ITmanager` trong ảnh. Khi khởi động, ứng dụng tạo database nếu chưa có (cần quyền tạo database) và tự sinh các bảng cho các module. Cấu hình trong `.env` (không đưa file này lên Git); mặc định dùng Windows Authentication. Nếu dùng SQL Login, đặt `SQL_SERVER_AUTH=sql`, `SQL_SERVER_USER`, `SQL_SERVER_PASSWORD`. Máy cần cài Microsoft ODBC Driver 18 for SQL Server.

Lần đầu mở ứng dụng sẽ vào `/setup` để tạo Admin ban đầu; mật khẩu tối thiểu 12 ký tự và được băm PBKDF2. Sau đó đăng nhập, tạo hồ sơ nhân viên trước khi cấp tài khoản khác. Vai trò Viewer chỉ đọc; IT Staff thao tác nghiệp vụ; Admin quản trị danh mục và tài khoản. Phiên đăng nhập được giữ trong bộ nhớ và kết thúc khi ứng dụng khởi động lại. Máy chủ mặc định chỉ lắng nghe `127.0.0.1`; khi triển khai qua mạng cần đặt sau reverse proxy HTTPS.

Các luồng web hiện có:

- Tài sản: thêm, sửa, tìm kiếm, ghi lịch sử, quản lý đường dẫn tệp và tải ảnh/chứng từ (PDF, PNG, JPG, DOCX, XLSX, TXT; tối đa 5 MB mỗi yêu cầu); thanh lý là thao tác đổi trạng thái để bảo toàn lịch sử liên quan.
- Cấp phát: cấp phát cho nhân viên đang làm, thu hồi kèm tình trạng, cảnh báo phiếu quá hạn / nhân viên đã nghỉ và in danh sách bằng chức năng in của trình duyệt.
- Bảo trì: tạo/hoàn thành phiếu, ghi chi phí/linh kiện, xem lịch sử và lập lịch bảo trì định kỳ.
- Kiểm kê: tạo đợt theo toàn công ty, khu vực hoặc loại thiết bị; quét/nhập mã, đối chiếu thiếu/thừa/sai vị trí.
- License: quản lý số lượng và hạn, gán/thu hồi theo người dùng hoặc thiết bị, ghi nhận phần mềm cài đặt.
- Nhân viên: thêm/cập nhật và đánh dấu nghỉ; tài khoản đăng nhập, đổi mật khẩu và phân vai trò được quản lý trong Hệ thống.
- Báo cáo: tổng hợp theo loại, tình trạng, vị trí, phòng ban; chi phí theo tháng và cảnh báo bảo hành/license; xuất CSV tương thích Excel.
- Hệ thống: cấu hình danh mục và xem 200 hoạt động gần nhất.

Tệp tải lên được lưu trong `webapp/uploads/`, không nằm trong SQL Server. QR/barcode được nhận qua trường nhập mã (chưa tích hợp camera/đầu đọc chuyên dụng). Chưa có đồng bộ HR, xuất PDF báo cáo riêng, hoặc sao lưu/phục hồi tự động; cần cấu hình reverse proxy HTTPS và backup riêng trước khi triển khai production. SQLAlchemy `create_all()` chỉ bổ sung bảng mới, không migration các thay đổi cấu trúc cột hiện hữu.

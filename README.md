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

Ứng dụng kết nối SQL Server theo thông tin máy chủ `192.168.1.69` và database `ITmanager` trong ảnh. Khi khởi động, ứng dụng tạo database nếu chưa có (cần quyền tạo database) và tự sinh các bảng theo schema của 8 module. Tài sản, lịch sử thay đổi và phiếu bảo trì được lưu trực tiếp vào SQL Server. Các cột văn bản dùng Unicode để bảo toàn tiếng Việt. Nếu phát hiện schema văn bản cũ, ứng dụng chỉ tạo lại các bảng tương ứng khi tất cả còn trống; nếu đã có dữ liệu, ứng dụng dừng thay vì xóa dữ liệu. `create_all()` không tự cập nhật schema đã có, nên cần sao lưu và migration rõ ràng khi thay đổi schema. Cấu hình trong `.env` (không đưa file này lên Git); mặc định dùng Windows Authentication. Nếu dùng SQL Login, đặt `SQL_SERVER_AUTH=sql`, `SQL_SERVER_USER`, `SQL_SERVER_PASSWORD`. Có thể cấu hình named instance qua `SQL_SERVER_INSTANCE`; nếu đã có chuỗi kết nối, đặt `DATABASE_URL`. Máy cần cài Microsoft ODBC Driver 18 for SQL Server.

Các màn hình Cấp phát, Kiểm kê, Phần mềm, Nhân viên, Báo cáo và Hệ thống hiện vẫn là trang khung; bảng dữ liệu đã được tự tạo nhưng các luồng này chưa nối CRUD vào database. Tải tệp, xuất Excel/PDF, barcode/QR và sao lưu/phục hồi cũng cần triển khai tiếp.

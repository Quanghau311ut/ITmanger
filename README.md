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
python main.py
```

Có thể đổi cổng bằng `python main.py --port 8080`. Máy chủ mặc định chỉ lắng nghe trên `127.0.0.1`.

Chạy kiểm thử:

```powershell
python -m unittest discover -s tests
```

Giao diện web hiện hỗ trợ dashboard, tìm kiếm/thêm tài sản và tạo/theo dõi/hoàn tất phiếu bảo trì. Các màn hình Cấp phát, Kiểm kê, Phần mềm, Nhân viên, Báo cáo và Hệ thống đang là trang khung chờ tích hợp nghiệp vụ. Dữ liệu hiện chỉ lưu trong bộ nhớ và sẽ mất khi dừng ứng dụng; cơ sở dữ liệu, đăng nhập, tải tệp, xuất Excel/PDF, barcode/QR và sao lưu/phục hồi cần được triển khai tiếp.

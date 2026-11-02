# API phát hiện biển số

Backend Python dùng `models/v11/license-plate-finetune-v1n.pt` để tìm vùng biển số trong ảnh toàn xe/cảnh có xe. Mô hình được nạp một lần khi khởi động. Hiện chưa có API đọc ký tự (`recognition`).

Từ thư mục `backend/` trên Windows (Python 3.11), chỉnh `backend/.env` nếu cần rồi chạy:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```

`run.py` đọc `.env` để chọn host và port. Dừng bằng Ctrl+C trước khi khởi động lại để áp dụng thay đổi; không chạy hai server trên cùng cổng. `backend/.env` chỉ dùng tại máy này và được Git bỏ qua; `backend/.env.example` là mẫu cho bản sao mới.

| Biến | Mặc định | Công dụng |
| --- | --- | --- |
| `BACKEND_HOST` | `127.0.0.1` | Địa chỉ server lắng nghe. |
| `BACKEND_PORT` | `8000` | Cổng server; cập nhật `API_PROXY_PORT` của UI khi đổi. |
| `UI_URL` | `http://127.0.0.1` | Giao thức và host của UI, không gồm cổng; phải khớp `UI_HOST` trong `ui/.env`. |
| `UI_PORT` | `5173` | Cổng của UI; phải khớp `UI_PORT` trong `ui/.env`. |
| `MODEL_PATH` | `../models/v11/license-plate-finetune-v1n.pt` | Checkpoint, đường dẫn tương đối tính từ `backend/` hoặc đường dẫn tuyệt đối. |

Gửi ảnh bằng multipart field `file` tới `POST http://127.0.0.1:8000/api/v1/ocr/detect`. Hỗ trợ JPEG (kể cả MPO từ một số máy ảnh), PNG và WEBP, ảnh tối đa 10 MB và 25 triệu pixel; toàn bộ yêu cầu multipart giới hạn 10 MB + 64 KiB overhead. Ví dụ:

```powershell
curl.exe -F "file=@C:\path\to\car.jpg;type=image/jpeg" http://127.0.0.1:8000/api/v1/ocr/detect
```

Phản hồi thành công (tọa độ pixel trên ảnh gốc sau khi áp dụng EXIF orientation):

```json
{"boxes":[{"x1":100.0,"y1":50.0,"x2":240.0,"y2":110.0,"confidence":0.83}]}
```

Có thể có nhiều box; không phát hiện được trả `{"boxes":[]}`. Mô hình dùng ngưỡng confidence mặc định của Ultralytics (0.25), nên một box là dự đoán, không bảo đảm đúng. Ảnh hỏng hoặc nội dung không khớp kiểu tệp trả HTTP 400; quá giới hạn trả 413; kiểu tệp không hỗ trợ trả 415; `Origin` ngoài địa chỉ backend và `UI_URL:UI_PORT` trả 403. Chạy kiểm tra bằng `.venv\Scripts\python -m unittest -v test_app`. Giữ `BACKEND_HOST` trên loopback khi chạy cục bộ; nếu mở ra mạng công cộng, cần lớp bảo vệ truy cập riêng.

Checkpoint đi kèm ghi [AGPL-3.0](../models/v11/README.md) và cảnh báo tập kiểm thử bị trùng với tập huấn luyện; cần đánh giá lại trên ảnh thực tế trước khi dùng cho quyết định quan trọng hoặc triển khai có yêu cầu giấy phép khác.

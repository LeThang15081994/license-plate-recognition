# API phát hiện và nhận diện biển số

Backend dùng mô hình keypoint [YOLOv8m-Pose](https://huggingface.co/PrasannaBAImodel/license-plate-keypoint-detection) để phát hiện biển số và bốn góc trên ảnh gốc, nắn phối cảnh rồi đọc ký tự từ ảnh biển bằng [`fast-plate-ocr` `cct-s-v2-global-model`](https://github.com/ankandrew/fast-plate-ocr). OCR chạy trên CPU, nạp một lần khi có biển đầu tiên; kết quả OCR chưa được đánh giá trên bộ biển Việt Nam.

Từ thư mục `backend/` trên Windows (Python 3.11), chỉnh `.env` ở thư mục gốc repository nếu cần rồi chạy:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```

`run.py` đọc `.env` ở thư mục gốc để chọn host và port. Dừng bằng Ctrl+C trước khi cài thư viện hoặc khởi động lại để áp dụng thay đổi; không chạy hai server trên cùng cổng. File `.env` dùng chung cho backend, Vite và Docker Compose, được Git bỏ qua; `.env.example` là mẫu cho bản sao mới. OCR đọc hai file có sẵn tại `models/recognition/cct_s_v2_global.onnx` và `models/recognition/cct_s_v2_global_plate_config.yaml`; **không tải model khi chạy**.

Checkpoint không được commit vì có dung lượng 106 MB. Tải từ repository gốc và xác nhận SHA-256 trước khi chạy backend (lệnh dưới đây chạy từ **thư mục gốc của repo**):

```powershell
curl.exe -fL --create-dirs -o models/keypoint/license_plate_keypoint.pt "https://huggingface.co/PrasannaBAImodel/license-plate-keypoint-detection/resolve/main/license_plate_keypoint.pt?download=true"
certutil -hashfile models/keypoint/license_plate_keypoint.pt SHA256
```

SHA-256 của checkpoint đã đánh giá: `c3a0731508458915fb6b6d633d2376a3229490b74a985279910caffa3ece555b`. Không nạp file `.pt` từ nguồn không tin cậy: PyTorch checkpoint dùng cơ chế pickle.

| Biến | Mặc định | Công dụng |
| --- | --- | --- |
| `BACKEND_HOST` | `127.0.0.1` | Địa chỉ server lắng nghe. |
| `BACKEND_PORT` | `8000` | Cổng server; cập nhật `API_PROXY_PORT` của UI khi đổi. |
| `UI_URL` | `http://127.0.0.1` | Giao thức và host của UI, không gồm cổng; phải khớp `UI_HOST` trong `.env` gốc. |
| `UI_PORT` | `5173` | Cổng của UI; Vite và backend cùng đọc từ `.env` gốc. |
| `MODEL_PATH` | `../models/keypoint/license_plate_keypoint.pt` | Checkpoint keypoint, đường dẫn tương đối tính từ `backend/` hoặc đường dẫn tuyệt đối. |
| `DETECTION_CONFIDENCE` | `0.7` | Confidence tối thiểu để giữ kết quả phát hiện; ngưỡng được áp dụng cho model và kết quả có confidence **bằng 0.7 trở lên** mới được tính. |

Gửi ảnh bằng multipart field `file` tới `POST http://127.0.0.1:8000/api/v1/ocr/detect`. Hỗ trợ JPEG (kể cả MPO từ một số máy ảnh), PNG và WEBP, ảnh tối đa 10 MB và 25 triệu pixel; toàn bộ yêu cầu multipart giới hạn 10 MB + 64 KiB overhead. Ví dụ:

```powershell
curl.exe -F "file=@C:\path\to\car.jpg;type=image/jpeg" http://127.0.0.1:8000/api/v1/ocr/detect
```

Phản hồi thành công (tọa độ pixel trên ảnh gốc sau khi áp dụng EXIF orientation):

```json
{
  "boxes": [{"x1": 100.0, "y1": 50.0, "x2": 240.0, "y2": 110.0, "confidence": 0.83}],
  "plates": [{
    "image": "<base64 PNG>",
    "text": "51G74372",
    "aligned": true,
    "corners": [
      {"x": 106.0, "y": 54.0, "confidence": 0.97},
      {"x": 233.0, "y": 55.0, "confidence": 0.98},
      {"x": 231.0, "y": 106.0, "confidence": 0.96},
      {"x": 108.0, "y": 105.0, "confidence": 0.95}
    ]
  }]
}
```

`plates[i]` tương ứng `boxes[i]`; giải mã `image` từ base64 để lấy ảnh PNG biển số. `text` là chuỗi **model OCR dự đoán từ chính ảnh biển số này**, có thể rỗng nếu không đọc được; không suy ra từ confidence của bbox. `aligned: true` nghĩa là cả bốn keypoint đạt ngưỡng tin cậy, tứ giác hợp lệ và đã nắn phối cảnh; `false` nghĩa là ảnh đưa vào OCR là crop gốc từ box, **không khẳng định ảnh đã thẳng**. Kết quả detection có confidence nhỏ hơn `DETECTION_CONFIDENCE` bị loại; mặc định là `0.7`, tính cả giá trị đúng bằng ngưỡng.

`plates[i].corners` chứa bốn điểm **model dự đoán trên ảnh gốc** theo thứ tự trái-trên, phải-trên, phải-dưới, trái-dưới. Mỗi `confidence` là độ tin cậy của điểm, **khác** `boxes[i].confidence` (độ tin cậy phát hiện biển); giá trị có thể `null` nếu model không cung cấp độ tin cậy từng điểm. Kể cả khi `aligned: false`, bốn điểm dự đoán vẫn được trả về để kiểm tra; nếu model không trả đủ bốn điểm thì `corners` là `[]`. Tọa độ trả về là dự đoán thô, còn phép nắn giới hạn chúng trong biên ảnh. `aligned: true` không chứng minh hình nắn đúng bằng mắt.

Ảnh nắn dùng trực tiếp bốn góc model dự đoán trên ảnh gốc, chỉ giới hạn điểm nằm ngoài biên ảnh; **không thêm padding** cho tứ giác hay `boxes`. Khi không thể căn chỉnh, ảnh trả về vẫn là crop từ box gốc.

Giới hạn đã quan sát: ảnh xe chứa biển `SB 2642` cho một biển căn chỉnh thành công, nhưng crop 163 × 64 px chỉ chứa biển đó không được model keypoint phát hiện (`boxes: []`). Model huấn luyện cho ảnh xe/cảnh; không nên xem ảnh cắt rất sát biển là đầu vào được bảo đảm.

Model OCR đã được kiểm tra với một ảnh chứa biển một dòng `SB 2642` và trả `SB2642`. Chưa xác minh độ chính xác với biển hai dòng/biển Việt Nam; cần thử trên ảnh có nhãn trước khi dùng kết quả tự động.

Ảnh hỏng hoặc nội dung không khớp kiểu tệp trả HTTP 400; quá giới hạn trả 413; kiểu tệp không hỗ trợ trả 415; `Origin` ngoài địa chỉ backend và `UI_URL:UI_PORT` trả 403. Chạy kiểm tra bằng `.venv\Scripts\python -m unittest -v test_app`. Giữ `BACKEND_HOST` trên loopback khi chạy cục bộ; nếu mở ra mạng công cộng, cần lớp bảo vệ truy cập riêng.

Checkpoint keypoint ghi giấy phép [Apache-2.0](https://huggingface.co/PrasannaBAImodel/license-plate-keypoint-detection), nhưng model nền Ultralytics được ghi là AGPL-3.0 trong thẻ model: cần xem lại điều kiện cấp phép trước khi phân phối. Hiệu năng trên biển Việt Nam chưa được xác nhận bằng bộ kiểm thử riêng.

## Chạy bằng Docker

File `docker-compose.yml` chạy một service UI/API trên cổng `8000`, mount model read-only và giới hạn log Docker theo vòng quay: tối đa 3 MB mỗi file, giữ 3 file. Từ thư mục gốc repository:

```sh
docker compose up --build
```

Mở `http://localhost:8000/`; image hai stage (Node build UI, Python chạy UI/API) **không chứa model**. Trước khi chạy, copy model keypoint vào `models/keypoint/license_plate_keypoint.pt` và hai file OCR vào `models/recognition/` như trên. Compose mount `${MODELS_DIR:-./models}` thành `/app/models` ở chế độ read-only; trên server có thể đặt `MODELS_DIR` thành đường dẫn tuyệt đối tới thư mục chứa `keypoint/` và `recognition/`. Docker build, CI và container không tải model; nếu thiếu file keypoint backend không khởi động, nếu thiếu file OCR yêu cầu nhận diện sẽ lỗi. `.env` gốc, model trên máy phát triển và `ui/node_modules` không được đưa vào image. Docker Compose đọc `.env` gốc; khi chạy image, các biến `BACKEND_HOST`, `BACKEND_PORT` và `UI_PORT` dành cho phát triển cục bộ không thay thế cấu hình container (backend lắng nghe `0.0.0.0:8000`, Compose dùng `PORT` để công bố cổng). Để đổi cổng công bố, đặt `PORT` (ví dụ `PORT=8080 docker compose up --build`); nếu truy cập bằng tên miền khác `localhost`, đặt `UI_URL` thành giao thức và hostname thực tế (không có cổng), `PORT` bằng cổng public. Backend mặc định lắng nghe mọi interface **trong container**; không công bố trực tiếp lên Internet nếu chưa có lớp bảo vệ truy cập.

GitHub Actions tại `.github/workflows/image.yml` chạy kiểm tra UI, build image và kiểm tra Python/import trong image (không cần tải model) trên PR và các push vào `develop`, `main` hoặc tag `v*`. Vì model không nằm trong repository, CI không thể chạy backend integration test hoặc khởi động API; chạy `.venv\Scripts\python -m unittest -v test_app` và smoke test container sau khi mount model trên server. Sau khi kiểm tra thành công, workflow push image `ghcr.io/lethang15081994/license-plate-recognition` lên GHCR (`:develop`, `:main`/`:latest`, tag `v*` và SHA). `GITHUB_TOKEN` với quyền `packages: write` được workflow sử dụng, không cần PAT hoặc secret riêng. Để chạy image đã publish (PowerShell):

```powershell
$env:IMAGE = "ghcr.io/lethang15081994/license-plate-recognition:develop"
docker compose pull
docker compose up -d --no-build
```

Nếu package GHCR đang private, đăng nhập với quyền `read:packages` trước khi pull. Trước khi phân phối image, xem lại điều khoản AGPL của model Ultralytics đã nêu ở trên.

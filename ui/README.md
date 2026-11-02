# License Plate Recognition UI

Giao diện Vite + React + TypeScript: kéo/thả hoặc dùng nút **Tải ảnh** ở góc trên bên phải card để chọn ảnh JPG, PNG, WEBP (tối đa 10 MB). Sau khi chọn ảnh, nút đổi thành **Chọn ảnh khác**. Nhấn **Phát hiện biển số** để hiển thị viền xanh nối bốn góc biển số trên ảnh gốc; khi bốn góc không hợp lệ sẽ không vẽ đường viền. Sidebar bên phải hiển thị ảnh biển số đã hiệu chỉnh phối cảnh hoặc crop gốc kèm ghi chú khi chưa căn chỉnh được, cùng chuỗi OCR do `fast-plate-ocr` dự đoán bằng chữ lớn bên cạnh ảnh (không có nhãn lặp lại). Nếu model không đọc được chữ, UI hiển thị **Không đọc được ký tự.** Thông báo tải ảnh/phát hiện/lỗi xuất hiện ở góc dưới bên phải và tự ẩn sau 6 giây. Trên màn hình hẹp sidebar chuyển xuống dưới card.

Trước tiên, [chạy backend](../backend/README.md). Trong `.env` ở thư mục gốc repository, đặt đích proxy khớp host và port của backend, rồi chạy lệnh từ thư mục `ui/`:

```sh
npm install
npm run dev
npm run build
npm run check
```

`npm run check` chạy TypeScript, ESLint, Prettier, Vitest và build. Có thể chạy riêng `npm run typecheck`, `npm run lint`, `npm run format:check`, `npm run test`, `npm run build`. Dùng `npm run format` để định dạng mã.

`.env` ở thư mục gốc có giá trị chạy cục bộ và được Git bỏ qua; `.env.example` ở cùng thư mục là mẫu. Backend, Vite và Docker Compose đều đọc file này; URL chỉ gồm giao thức và host, còn cổng đặt ở biến riêng:

| Biến             | Mặc định           | Công dụng                                                   |
| ---------------- | ------------------ | ----------------------------------------------------------- |
| `UI_HOST`        | `127.0.0.1`        | Host của Vite; khi đổi, cập nhật `UI_URL` trong `.env` gốc. |
| `UI_PORT`        | `5173`             | Cổng Vite; backend đọc cùng biến từ `.env` gốc.             |
| `API_PROXY_URL`  | `http://127.0.0.1` | Giao thức và host để Vite gọi backend.                      |
| `API_PROXY_PORT` | `8000`             | Cổng backend; phải khớp `BACKEND_PORT` trong `.env` gốc.    |

Khởi động lại Vite và backend sau khi sửa `.env`. Nếu port đã có server khác sử dụng, Vite báo lỗi thay vì tự đổi cổng.

`docker-compose.yml` ở thư mục gốc build UI và phục vụ UI/API trong **một image, một origin** qua backend; xem [hướng dẫn Docker](../backend/README.md#chạy-bằng-docker). Các biến proxy trong `.env` gốc chỉ áp dụng cho Vite dev server; image cần mount model từ máy chạy. Không cần Nginx khi dùng cách triển khai này vì backend phục vụ trực tiếp UI đã build; nếu công bố trên Internet, đặt origin phù hợp và thêm lớp bảo vệ truy cập.

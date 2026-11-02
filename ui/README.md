# License Plate Recognition UI

Giao diện Vite + React + TypeScript: kéo/thả hoặc chọn ảnh JPG, PNG, WEBP (tối đa 10 MB), xem trước ảnh, rồi nhấn **Phát hiện biển số** để hiển thị các khung do backend dự đoán. Vùng văn bản vẫn chỉ hiển thị trạng thái; chưa có dịch vụ đọc ký tự và không tạo văn bản nhận diện giả.

Trước tiên, [chạy backend](../backend/README.md). Trong `ui/.env`, đặt đích proxy khớp host và port của backend, rồi chạy lệnh từ thư mục `ui/`:

```sh
npm install
npm run dev
npm run build
npm run check
```

`npm run check` chạy TypeScript, ESLint, Prettier, Vitest và build. Có thể chạy riêng `npm run typecheck`, `npm run lint`, `npm run format:check`, `npm run test`, `npm run build`. Dùng `npm run format` để định dạng mã.

`ui/.env` có giá trị mặc định và được Git bỏ qua; `ui/.env.example` là mẫu. URL chỉ gồm giao thức và host, còn cổng đặt ở biến riêng:

| Biến | Mặc định | Công dụng |
| --- | --- | --- |
| `UI_HOST` | `127.0.0.1` | Host của Vite; khi đổi, cập nhật `UI_URL` trong `backend/.env`. |
| `UI_PORT` | `5173` | Cổng của Vite; khi đổi, cập nhật `UI_PORT` trong `backend/.env`. |
| `API_PROXY_URL` | `http://127.0.0.1` | Giao thức và host để Vite gọi backend. |
| `API_PROXY_PORT` | `8000` | Cổng backend; phải khớp `BACKEND_PORT` trong `backend/.env`. |

Khởi động lại Vite và backend sau khi sửa `.env`. Nếu port đã có server khác sử dụng, Vite báo lỗi thay vì tự đổi cổng.

Bản build chưa có cấu hình triển khai: để đưa lên máy chủ, cần chuyển tiếp `/api/*` cùng origin với UI và cấu hình origin hợp lệ tại backend kèm bảo vệ truy cập. Các biến proxy trong `.env` chỉ áp dụng cho dev server, không đổi API trong bản build.

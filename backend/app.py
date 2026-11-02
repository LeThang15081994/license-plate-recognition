import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.responses import JSONResponse
from ultralytics import YOLO

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
MODEL_PATH = (BACKEND_DIR / os.getenv("MODEL_PATH", "../models/v11/license-plate-finetune-v1n.pt")).resolve()
UI_URL = os.getenv("UI_URL", "http://127.0.0.1").rstrip("/")
UI_PORT = int(os.getenv("UI_PORT", "5173"))
ALLOWED_ORIGINS = {
    f"http://{BACKEND_HOST}:{BACKEND_PORT}".encode(),
    f"{UI_URL}:{UI_PORT}".encode(),
}
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
IMAGE_FORMATS = {"image/jpeg": {"JPEG", "MPO"}, "image/png": {"PNG"}, "image/webp": {"WEBP"}}


class UploadBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/api/v1/ocr/detect":
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        origin = headers.get(b"origin")
        if origin and origin not in ALLOWED_ORIGINS:
            await JSONResponse({"detail": "Origin không được phép."}, status_code=403)(scope, receive, send)
            return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_FILE_SIZE + 65536:
                    raise HTTPException(status_code=413, detail="Yêu cầu vượt quá 10 MB.")
            return message

        await self.app(scope, limited_receive, send)


app = FastAPI()
app.add_middleware(UploadBoundary)
model = YOLO(MODEL_PATH)


@app.post("/api/v1/ocr/detect")
def detect(file: UploadFile) -> dict:
    if file.content_type not in IMAGE_FORMATS:
        raise HTTPException(status_code=415, detail="Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP.")

    file.file.seek(0, 2)
    size = file.file.tell()
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Ảnh phải có dung lượng tối đa 10 MB.")
    file.file.seek(0)

    try:
        with Image.open(file.file) as source:
            if source.format not in IMAGE_FORMATS[file.content_type]:
                raise HTTPException(status_code=400, detail="Nội dung ảnh không khớp định dạng tệp.")
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail="Ảnh có kích thước quá lớn.")
            source.load()
            image = ImageOps.exif_transpose(source) if source.getexif().get(274, 1) != 1 else source
            rgb_image = image if image.mode == "RGB" else image.convert("RGB")
            result = model.predict(rgb_image, verbose=False)[0]
    except Image.DecompressionBombError as exc:
        raise HTTPException(status_code=413, detail="Ảnh có kích thước quá lớn.") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Không đọc được ảnh.") from exc

    return {
        "boxes": [
            {"x1": xyxy[0], "y1": xyxy[1], "x2": xyxy[2], "y2": xyxy[3], "confidence": confidence}
            for xyxy, confidence in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist())
        ]
    }

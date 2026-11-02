import base64
import io
import os
from functools import cache
from pathlib import Path

import numpy as np

from alignment import align_plate
from dotenv import load_dotenv
from fast_plate_ocr import LicensePlateRecognizer
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.responses import JSONResponse
from ultralytics import YOLO

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR.parent / ".env")
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
MODEL_PATH = (BACKEND_DIR / os.getenv("MODEL_PATH", "../models/keypoint/license_plate_keypoint.pt")).resolve()
OCR_MODEL_DIR = BACKEND_DIR.parent / "models" / "recognition"
DETECTION_CONFIDENCE = float(os.getenv("DETECTION_CONFIDENCE", "0.7"))
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


@cache
def get_recognizer():
    return LicensePlateRecognizer(
        onnx_model_path=OCR_MODEL_DIR / "cct_s_v2_global.onnx",
        plate_config_path=OCR_MODEL_DIR / "cct_s_v2_global_plate_config.yaml",
        device="cpu",
    )


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
            result = model.predict(rgb_image, conf=DETECTION_CONFIDENCE, verbose=False)[0]
            coordinates = result.boxes.xyxy.tolist()
            confidences = result.boxes.conf.tolist()
            selected_indices = [
                index for index, confidence in enumerate(confidences) if confidence >= DETECTION_CONFIDENCE
            ]
            keypoints = result.keypoints
            corners = keypoints.xy.tolist() if keypoints is not None else []
            visibility = keypoints.conf.tolist() if keypoints is not None and keypoints.conf is not None else []
            pixels = np.asarray(rgb_image) if selected_indices else None
            plates = []
            plate_images = []
            for index in selected_indices:
                box = coordinates[index]
                plate_corners = corners[index] if index < len(corners) else []
                corner_scores = visibility[index] if index < len(visibility) else []
                plate, aligned = align_plate(
                    pixels,
                    box,
                    plate_corners,
                    corner_scores,
                )
                plate_images.append(np.asarray(plate))
                output = io.BytesIO()
                plate.save(output, format="PNG")
                plates.append(
                    {
                        "image": base64.b64encode(output.getvalue()).decode("ascii"),
                        "aligned": aligned,
                        "corners": [
                            {
                                "x": point[0],
                                "y": point[1],
                                "confidence": corner_scores[point_index] if point_index < len(corner_scores) else None,
                            }
                            for point_index, point in enumerate(plate_corners)
                        ]
                        if len(plate_corners) == 4
                        else [],
                    }
                )
    except Image.DecompressionBombError as exc:
        raise HTTPException(status_code=413, detail="Ảnh có kích thước quá lớn.") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Không đọc được ảnh.") from exc

    predictions = get_recognizer().run(plate_images) if plate_images else []

    return {
        "boxes": [
            {"x1": coordinates[index][0], "y1": coordinates[index][1], "x2": coordinates[index][2], "y2": coordinates[index][3], "confidence": confidences[index]}
            for index in selected_indices
        ],
        "plates": [{**plate, "text": prediction.plate} for plate, prediction in zip(plates, predictions, strict=True)],
    }

STATIC_DIR = BACKEND_DIR / "static"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")

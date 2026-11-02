import io
import struct
import zlib
import unittest

from fastapi.testclient import TestClient
from PIL import Image

from app import app


class DetectApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_rejects_unsupported_corrupt_and_oversized_images(self):
        cases = [
            (b"plain text", "text/plain", 415),
            (b"not a png", "image/png", 400),
            (b"x" * (10 * 1024 * 1024 + 1), "image/jpeg", 413),
        ]
        chunk = lambda kind, body: struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
        bomb = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 15000, 15000, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0" * 45001))
            + chunk(b"IEND", b"")
        )
        cases.append((bomb, "image/png", 413))
        for content, media_type, status in cases:
            with self.subTest(media_type=media_type, status=status):
                response = self.client.post(
                    "/api/v1/ocr/detect",
                    files={"file": ("image", content, media_type)},
                )
                self.assertEqual(response.status_code, status)

    def test_rejects_untrusted_origin_and_total_request_size(self):
        image = io.BytesIO()
        Image.new("RGB", (64, 64), "white").save(image, format="PNG")
        response = self.client.post(
            "/api/v1/ocr/detect",
            files={"file": ("car.png", image.getvalue(), "image/png")},
            headers={"Origin": "https://untrusted.example"},
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            "/api/v1/ocr/detect",
            files={
                "file": ("a.png", b"x" * (6 * 1024 * 1024), "image/png"),
                "extra": ("b.png", b"x" * (6 * 1024 * 1024), "image/png"),
            },
        )
        self.assertEqual(response.status_code, 413)

    def test_rejects_origin_matching_spoofed_host(self):
        image = io.BytesIO()
        Image.new("RGB", (64, 64), "white").save(image, format="PNG")
        response = self.client.post(
            "/api/v1/ocr/detect",
            files={"file": ("scene.png", image.getvalue(), "image/png")},
            headers={"Origin": "http://attacker.example", "Host": "attacker.example"},
        )
        self.assertEqual(response.status_code, 403)

    def test_accepts_multipicture_jpeg(self):
        image = io.BytesIO()
        Image.new("RGB", (64, 64), "white").save(
            image,
            format="MPO",
            save_all=True,
            append_images=[Image.new("RGB", (64, 64), "black")],
        )
        response = self.client.post(
            "/api/v1/ocr/detect",
            files={"file": ("scene.jpg", image.getvalue(), "image/jpeg")},
        )
        self.assertEqual(response.status_code, 200)

    def test_accepts_image_and_returns_original_pixel_boxes(self):
        image = io.BytesIO()
        Image.new("RGB", (640, 480), "white").save(image, format="PNG")
        response = self.client.post(
            "/api/v1/ocr/detect",
            files={"file": ("scene.png", image.getvalue(), "image/png")},
        )
        self.assertEqual(response.status_code, 200)
        boxes = response.json()["boxes"]
        self.assertIsInstance(boxes, list)
        for box in boxes:
            self.assertEqual(set(box), {"x1", "y1", "x2", "y2", "confidence"})
            self.assertLessEqual(0, box["x1"])
            self.assertLess(box["x1"], box["x2"])
            self.assertLessEqual(box["x2"], 640)
            self.assertLessEqual(0, box["y1"])
            self.assertLess(box["y1"], box["y2"])
            self.assertLessEqual(box["y2"], 480)
            self.assertLessEqual(0, box["confidence"])
            self.assertLessEqual(box["confidence"], 1)


if __name__ == "__main__":
    unittest.main()

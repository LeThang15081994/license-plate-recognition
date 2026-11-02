import base64
import io
import struct
import zlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app import app


def pose_result(boxes, corners, visibility):
    return [
        SimpleNamespace(
            boxes=SimpleNamespace(
                xyxy=SimpleNamespace(tolist=lambda: [box[:4] for box in boxes]),
                conf=SimpleNamespace(tolist=lambda: [box[4] for box in boxes]),
            ),
            keypoints=SimpleNamespace(
                xy=SimpleNamespace(tolist=lambda: corners),
                conf=SimpleNamespace(tolist=lambda: visibility),
            ),
        )
    ]


class DetectApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ocr = patch(
            "app.get_recognizer",
            return_value=SimpleNamespace(run=lambda images: [SimpleNamespace(plate="") for _ in images]),
        )
        cls.ocr.start()
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.ocr.stop()

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

    def test_only_returns_detections_at_or_above_configured_confidence(self):
        image = io.BytesIO()
        Image.new("RGB", (300, 100), "white").save(image, format="PNG")
        predictions = pose_result(
            [[10, 10, 60, 40, 0.699], [80, 10, 130, 40, 0.7], [160, 10, 210, 40, 0.701]],
            [
                [(10, 10), (60, 10), (60, 40), (10, 40)],
                [(80, 10), (130, 10), (130, 40), (80, 40)],
                [(160, 10), (210, 10), (210, 40), (160, 40)],
            ],
            [[0.99] * 4, [0.99] * 4, [0.99] * 4],
        )
        with patch("app.model.predict", return_value=predictions) as predict:
            response = self.client.post(
                "/api/v1/ocr/detect",
                files={"file": ("scene.png", image.getvalue(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([box["confidence"] for box in response.json()["boxes"]], [0.7, 0.701])
        self.assertEqual(
            [plate["corners"][0]["x"] for plate in response.json()["plates"]],
            [80, 160],
        )
        self.assertEqual(predict.call_args.kwargs["conf"], 0.7)

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


    def test_recognizes_plates_from_returned_crops_in_detection_order(self):
        content = io.BytesIO()
        Image.new("RGB", (220, 120), "white").save(content, format="PNG")
        predictions = pose_result(
            [[5, 10, 95, 65, 0.9], [105, 20, 210, 95, 0.8]],
            [
                [(5, 10), (95, 10), (95, 65), (5, 65)],
                [(105, 20), (210, 20), (210, 95), (105, 95)],
            ],
            [[0.99] * 4, [0.99, 0.99, 0.0, 0.99]],
        )
        recognize = SimpleNamespace(
            run=Mock(return_value=[SimpleNamespace(plate="51G74372"), SimpleNamespace(plate="SB2642")])
        )
        with patch("app.model.predict", return_value=predictions), patch(
            "app.get_recognizer", return_value=recognize
        ):
            response = self.client.post(
                "/api/v1/ocr/detect",
                files={"file": ("scene.png", content.getvalue(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        plates = response.json()["plates"]
        self.assertEqual([plate["text"] for plate in plates], ["51G74372", "SB2642"])
        self.assertEqual([plate["aligned"] for plate in plates], [True, False])
        ocr_images = recognize.run.call_args.args[0]
        self.assertEqual(len(ocr_images), 2)
        for plate, ocr_image in zip(plates, ocr_images):
            with Image.open(io.BytesIO(base64.b64decode(plate["image"]))) as crop:
                np.testing.assert_array_equal(ocr_image, np.asarray(crop))

    def test_returns_rectified_plate_for_skewed_detection(self):
        image = Image.new("RGB", (300, 180), (90, 90, 90))
        corners = [(55, 40), (260, 65), (235, 140), (35, 115)]
        draw = ImageDraw.Draw(image)
        draw.polygon(corners, fill="white")
        for x in range(70, 240, 20):
            draw.line((x, 55, x - 12, 130), fill="black", width=6)
        content = io.BytesIO()
        image.save(content, format="PNG")
        predictions = pose_result(
            [[35, 40, 260, 140, 0.9]],
            [[corners[0], corners[1], corners[2], corners[3]]],
            [[0.98] * 4],
        )
        with patch("app.model.predict", return_value=predictions):
            response = self.client.post(
                "/api/v1/ocr/detect",
                files={"file": ("scene.png", content.getvalue(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["plates"]), 1)
        plate = response.json()["plates"][0]
        self.assertTrue(plate["aligned"])
        with Image.open(io.BytesIO(base64.b64decode(plate["image"]))) as aligned:
            self.assertEqual(aligned.size, (207, 79))
            self.assertGreater(aligned.width, aligned.height)
            self.assertGreater(aligned.getpixel((aligned.width // 10, aligned.height // 10))[0], 190)
            self.assertGreater(aligned.getpixel((aligned.width * 9 // 10, aligned.height // 10))[0], 190)

    def test_aligns_plate_just_outside_detection_box(self):
        image = Image.new("RGB", (300, 160), (90, 90, 90))
        ImageDraw.Draw(image).polygon([(51, 38), (241, 36), (247, 121), (55, 126)], fill="white")
        content = io.BytesIO()
        image.save(content, format="PNG")
        predictions = pose_result(
            [[70, 40, 230, 120, 0.9]],
            [[(51, 38), (241, 36), (247, 121), (55, 126)]],
            [[0.98] * 4],
        )
        with patch("app.model.predict", return_value=predictions):
            response = self.client.post(
                "/api/v1/ocr/detect",
                files={"file": ("scene.png", content.getvalue(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["boxes"][0]["x1"], 70)
        plate = response.json()["plates"][0]
        self.assertEqual(
            plate["corners"],
            [
                {"x": 51, "y": 38, "confidence": 0.98},
                {"x": 241, "y": 36, "confidence": 0.98},
                {"x": 247, "y": 121, "confidence": 0.98},
                {"x": 55, "y": 126, "confidence": 0.98},
            ],
        )
        self.assertTrue(plate["aligned"])
        with Image.open(io.BytesIO(base64.b64decode(plate["image"]))) as aligned:
            self.assertGreater(aligned.width, 160)


    def test_returns_unaligned_crop_when_edges_are_not_visible(self):
        content = io.BytesIO()
        Image.new("RGB", (100, 60), (80, 90, 100)).save(content, format="PNG")
        predictions = pose_result(
            [[20, 10, 80, 50, 0.8]],
            [[(20, 10), (80, 10), (80, 50), (20, 50)]],
            [[0.98, 0.98, 0.12, 0.98]],
        )
        with patch("app.model.predict", return_value=predictions):
            response = self.client.post(
                "/api/v1/ocr/detect",
                files={"file": ("scene.png", content.getvalue(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        plate = response.json()["plates"][0]
        self.assertFalse(plate["aligned"])
        self.assertEqual(len(plate["corners"]), 4)
        self.assertEqual(plate["corners"][2], {"x": 80, "y": 50, "confidence": 0.12})
        with Image.open(io.BytesIO(base64.b64decode(plate["image"]))) as crop:
            self.assertEqual(crop.size, (60, 40))
            self.assertEqual(crop.getpixel((30, 20)), (80, 90, 100))

    def test_aligns_plate_at_image_edge_and_preserves_multiple_results(self):
        image = Image.new("RGB", (240, 80), (70, 80, 90))
        draw = ImageDraw.Draw(image)
        draw.polygon([(0, 0), (105, 6), (104, 70), (0, 70)], fill=(255, 240, 20))
        draw.rectangle((145, 15, 224, 65), fill=(10, 100, 240))
        content = io.BytesIO()
        image.save(content, format="PNG")
        predictions = pose_result(
            [[1, 2, 105, 70, 0.9], [145, 15, 225, 66, 0.8]],
            [
                [(0, 0), (105, 6), (104, 70), (0, 70)],
                [(145, 15), (224, 15), (224, 65), (145, 65)],
            ],
            [[0.99] * 4, [0.99, 0.99, 0.0, 0.99]],
        )
        with patch("app.model.predict", return_value=predictions):
            response = self.client.post(
                "/api/v1/ocr/detect",
                files={"file": ("scene.png", content.getvalue(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        plates = response.json()["plates"]
        self.assertEqual(len(plates), 2)
        self.assertTrue(plates[0]["aligned"])
        self.assertFalse(plates[1]["aligned"])
        self.assertEqual(plates[0]["corners"][0], {"x": 0, "y": 0, "confidence": 0.99})
        self.assertEqual(plates[1]["corners"][0], {"x": 145, "y": 15, "confidence": 0.99})
        self.assertEqual(plates[1]["corners"][2]["confidence"], 0.0)
        with Image.open(io.BytesIO(base64.b64decode(plates[0]["image"]))) as aligned:
            self.assertGreater(aligned.getpixel((aligned.width // 2, aligned.height // 2))[0], 220)
        with Image.open(io.BytesIO(base64.b64decode(plates[1]["image"]))) as fallback:
            self.assertEqual(fallback.size, (80, 51))
            self.assertEqual(fallback.getpixel((30, 20)), (10, 100, 240))


    def test_does_not_claim_alignment_for_collapsed_keypoints(self):
        image = Image.new("RGB", (120, 80), (45, 55, 65))
        content = io.BytesIO()
        image.save(content, format="PNG")
        predictions = pose_result(
            [[20, 10, 90, 60, 0.8]],
            [[(40, 20), (60, 20), (60, 50), (40, 50)]],
            [[0.99] * 4],
        )
        with patch("app.model.predict", return_value=predictions):
            response = self.client.post(
                "/api/v1/ocr/detect",
                files={"file": ("scene.png", content.getvalue(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        plate = response.json()["plates"][0]
        self.assertFalse(plate["aligned"])
        with Image.open(io.BytesIO(base64.b64decode(plate["image"]))) as fallback:
            self.assertEqual(fallback.size, (70, 50))

if __name__ == "__main__":
    unittest.main()

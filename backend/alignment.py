"""Rectify a plate from four predicted corner keypoints."""

import cv2
import numpy as np
from PIL import Image

MIN_KEYPOINT_CONFIDENCE = 0.5
MIN_QUAD_BOX_AREA_RATIO = 0.3


def align_plate(
    image: np.ndarray,
    box: list[float],
    corners: list[list[float]] | None,
    visibility: list[float] | None,
) -> tuple[Image.Image, bool]:
    x1, y1, x2, y2 = box
    left, top = max(0, int(x1)), max(0, int(y1))
    right, bottom = min(image.shape[1], int(np.ceil(x2))), min(image.shape[0], int(np.ceil(y2)))

    if (
        right - left >= 20
        and bottom - top >= 10
        and corners is not None
        and len(corners) == 4
        and visibility is not None
        and len(visibility) == 4
        and all(score >= MIN_KEYPOINT_CONFIDENCE for score in visibility)
    ):
        points = np.asarray(corners, dtype=np.float32)
        if points.shape == (4, 2) and np.isfinite(points).all():
            np.clip(points[:, 0], 0, image.shape[1] - 1, out=points[:, 0])
            np.clip(points[:, 1], 0, image.shape[0] - 1, out=points[:, 1])
            width = round(max(np.linalg.norm(points[1] - points[0]), np.linalg.norm(points[2] - points[3])))
            height = round(max(np.linalg.norm(points[3] - points[0]), np.linalg.norm(points[2] - points[1])))
            if (
                width >= 20
                and height >= 10
                and cv2.isContourConvex(points.reshape(4, 1, 2))
                and cv2.contourArea(points) >= MIN_QUAD_BOX_AREA_RATIO * (right - left) * (bottom - top)
            ):
                target = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
                transform = cv2.getPerspectiveTransform(points, target)
                return Image.fromarray(cv2.warpPerspective(image, transform, (width, height))), True

    return Image.fromarray(image[top:bottom, left:right]), False

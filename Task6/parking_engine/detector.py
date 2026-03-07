"""Encapsulate YOLO-based license plate detection."""
from ultralytics import YOLO
import numpy as np


class PlateDetector:
    """Wrapper around a YOLO object for ease of reuse and testing."""

    def __init__(self, model_path: str):
        if not model_path:
            raise ValueError("model_path must be provided")
        self._model = YOLO(model_path)

    def locate_plate(self, frame_bgr: np.ndarray):
        """Return the bounding box of the first detected plate.

        Args:
            frame_bgr: BGR image as a numpy array.

        Returns:
            Tuple[x1, y1, x2, y2] or None if nothing found.
        """
        res = self._model(frame_bgr, save=False, verbose=False)
        boxes = res[0].boxes.xyxy.cpu().numpy().astype(int)
        if boxes.size == 0:
            return None
        x1, y1, x2, y2 = boxes[0]
        return int(x1), int(y1), int(x2), int(y2)

    @staticmethod
    def crop_region(image: np.ndarray, bbox, padding: int = 4):
        """Extract a padded slice of the original frame.

        Bounding box is clipped to image dimensions automatically.
        """
        if bbox is None:
            return None
        x1, y1, x2, y2 = bbox
        h, w = image.shape[:2]
        top = max(0, y1 - padding)
        left = max(0, x1 - padding)
        bottom = min(h, y2 + padding)
        right = min(w, x2 + padding)
        return image[top:bottom, left:right]

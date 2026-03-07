"""Lightweight Flask server for the parking slip service.

The original implementation hard‑coded YOLO/EasyOCR calls; this
version uses the `parking_engine` helpers so the logic is the same but
code shape is very different.
"""

import logging
import os
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, send_from_directory

# helpers from our library
from parking_engine import config
from parking_engine.detector import PlateDetector
from parking_engine.ocr import OcrProcessor
from parking_engine.slip import SlipCreator

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("parking_api")

# constants (reuse config values)
SLIP_DIR = config.SLIP_FOLDER
os.makedirs(SLIP_DIR, exist_ok=True)

# instantiate once at module load
_plate_detector = PlateDetector(config.MODEL_WEIGHTS)
_ocr = OcrProcessor(languages=config.OCR_LANGUAGES, use_gpu=True, min_confidence=config.OCR_MIN_CONFIDENCE)
_slip_srv = SlipCreator(config.BOLD_FONT, config.REGULAR_FONT, fee=config.PARKING_FEE)


@app.route("/")
def index_page():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_image_upload():
    file = request.files.get("image")
    if not file:
        return jsonify(error="No file"), 400

    img_arr = np.frombuffer(file.read(), dtype=np.uint8)
    frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify(error="cannot decode"), 400

    bbox = _plate_detector.locate_plate(frame)
    if bbox is None:
        return jsonify(error="no plate detected"), 200

    crop = _plate_detector.crop_region(frame, bbox)
    plate_text = _ocr.extract_text(crop)

    # annotate
    x1, y1, x2, y2 = bbox
    annotated = frame.copy()
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 200, 0), 2)
    cv2.imwrite(os.path.join(SLIP_DIR, "annotated_latest.jpg"), annotated)
    cv2.imwrite(os.path.join(SLIP_DIR, "crop_latest.jpg"), crop)

    now = datetime.now()
    slip_name = _slip_srv.make_receipt(plate_text, now, os.path.join(SLIP_DIR, f"slip_{now.strftime('%Y%m%d_%H%M%S')}.png"))

    return jsonify(
        plate=plate_text,
        entry_time=now.strftime("%d %b %Y, %H:%M:%S"),
        fee=config.PARKING_FEE,
        slip_url=f"/static/slips/{os.path.basename(slip_name)}",
        anno_url="/static/slips/annotated_latest.jpg",
        crop_url="/static/slips/crop_latest.jpg",
    )


@app.route("/static/slips/<path:filename>")
def serve_generated_slip(filename):
    return send_from_directory(SLIP_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

import logging
import os
from datetime import datetime

import cv2
import easyocr
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, jsonify, render_template, request, send_from_directory
from ultralytics import YOLO




app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("smart_parking_flask")




MODEL_PATH = "best.pt"
SLIP_DIR = os.path.join("static", "slips")
FONT_BOLD_PATH = os.path.join("fonts", "Poppins", "Poppins-Bold.ttf")
FONT_REG_PATH = os.path.join("fonts", "Poppins", "Poppins-Regular.ttf")
OCR_MIN_CONF = 0.2

os.makedirs(SLIP_DIR, exist_ok=True)


log.info("Loading YOLO and EasyOCR models...")
detector = YOLO(MODEL_PATH)
ocr_reader = easyocr.Reader(["en"], gpu=True)
log.info("Models loaded successfully.")



def first_plate_bbox(image_bgr: np.ndarray):
    prediction = detector(image_bgr, save=False, verbose=False)
    bbox_array = prediction[0].boxes.xyxy.cpu().numpy().astype(int)

    if len(bbox_array) == 0:
        return None

    x1, y1, x2, y2 = bbox_array[0]
    return int(x1), int(y1), int(x2), int(y2)


def crop_plate(image_bgr: np.ndarray, bbox, pad: int = 4):
    x1, y1, x2, y2 = bbox

    top = max(0, y1 - pad)
    bottom = min(image_bgr.shape[0], y2 + pad)
    left = max(0, x1 - pad)
    right = min(image_bgr.shape[1], x2 + pad)

    return image_bgr[top:bottom, left:right]


def ocr_plate_text(plate_region: np.ndarray):
    if plate_region.size == 0:
        return "Crop Error"

    raw_items = ocr_reader.readtext(plate_region, detail=1, paragraph=False)
    log.info("OCR output: %s", raw_items)

    merged_tokens = []
    for _, token, conf in raw_items:
        if conf < OCR_MIN_CONF:
            continue

        normalized = "".join(ch for ch in token if ch.isalnum()).upper()
        if normalized:
            merged_tokens.append(normalized)

    return " ".join(merged_tokens) if merged_tokens else "No text detected"



def load_fonts():
    try:
        heading = ImageFont.truetype(FONT_BOLD_PATH, 30)
        label = ImageFont.truetype(FONT_REG_PATH, 16)
        value = ImageFont.truetype(FONT_BOLD_PATH, 18)
        small = ImageFont.truetype(FONT_REG_PATH, 12)
        return heading, label, value, small
    except Exception:
        fallback = ImageFont.load_default()
        return fallback, fallback, fallback, fallback


def generate_slip_png(plate_text: str, entry_dt: datetime):
    width, height = 600, 380

    colors = {
        "bg": "#0D0D1A",
        "primary": "#7C3AED",
        "label": "#A78BFA",
        "main_text": "#FFFFFF",
        "muted": "#94A3B8",
        "border": "#4C1D95",
    }

    canvas = Image.new("RGB", (width, height), colors["bg"])
    draw = ImageDraw.Draw(canvas)
    f_title, f_label, f_value, f_small = load_fonts()

    draw.rounded_rectangle([12, 12, width - 12, height - 12], radius=14, outline=colors["border"], width=2)
    draw.rounded_rectangle([12, 12, width - 12, 60], radius=14, fill=colors["primary"])

    title = "PARKING RECEIPT"
    tbox = draw.textbbox((0, 0), title, font=f_title)
    tw = tbox[2] - tbox[0]
    draw.text(((width - tw) / 2, 18), title, font=f_title, fill=colors["main_text"])

    draw.line([(40, 75), (width - 40, 75)], fill=colors["border"], width=1)

    fields = [
        ("Vehicle Plate", plate_text),
        ("Entry Time", entry_dt.strftime("%d %b %Y  %H:%M:%S")),
        ("Parking Fee", "Rs. 30.00"),
        ("Status", "ACTIVE"),
    ]

    y = 95
    for key, val in fields:
        draw.text((50, y), key, font=f_label, fill=colors["label"])
        draw.text((270, y), val, font=f_value, fill=colors["main_text"])
        y += 55

    footer = "Powered by Smart Parking System  •  YOLO + EasyOCR"
    fbox = draw.textbbox((0, 0), footer, font=f_small)
    fw = fbox[2] - fbox[0]
    draw.text(((width - fw) / 2, height - 30), footer, font=f_small, fill=colors["muted"])

    safe_plate = plate_text.replace(" ", "_")
    out_name = f"slip_{safe_plate}_{entry_dt.strftime('%Y%m%d_%H%M%S')}.png"
    full_out_path = os.path.join(SLIP_DIR, out_name)
    canvas.save(full_out_path)

    log.info("Slip generated at %s", full_out_path)
    return out_name


@app.route("/")
def index_page():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_image_upload():
    uploaded = request.files.get("image")
    if uploaded is None:
        return jsonify({"error": "No image uploaded"}), 400

    if uploaded.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    img_bytes = np.frombuffer(uploaded.read(), dtype=np.uint8)
    image_bgr = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
    if image_bgr is None:
        return jsonify({"error": "Could not decode image"}), 400

    bbox = first_plate_bbox(image_bgr)
    if bbox is None:
        return jsonify({"error": "No number plate detected in image"}), 200

    plate_crop = crop_plate(image_bgr, bbox, pad=4)
    plate_text = ocr_plate_text(plate_crop)

    x1, y1, x2, y2 = bbox
    annotated = image_bgr.copy()
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (124, 58, 237), 3)

    cv2.imwrite(os.path.join(SLIP_DIR, "annotated_latest.jpg"), annotated)
    cv2.imwrite(os.path.join(SLIP_DIR, "crop_latest.jpg"), plate_crop)

    now = datetime.now()
    slip_file = generate_slip_png(plate_text, now)

    return jsonify(
        {
            "plate": plate_text,
            "entry_time": now.strftime("%d %b %Y, %H:%M:%S"),
            "fee": "Rs. 30.00",
            "slip_url": f"/static/slips/{slip_file}",
            "anno_url": "/static/slips/annotated_latest.jpg",
            "crop_url": "/static/slips/crop_latest.jpg",
        }
    )


@app.route("/static/slips/<path:filename>")
def serve_generated_slip(filename):
    return send_from_directory(SLIP_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

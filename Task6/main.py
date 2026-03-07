import logging
import os
from datetime import datetime

import cv2
import easyocr
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO




MODEL_FILE = "best.pt"
FONT_FOLDER = "fonts"
REGULAR_FONT = os.path.join(FONT_FOLDER, "Poppins-Regular.ttf")
BOLD_FONT = os.path.join(FONT_FOLDER, "Poppins-Bold.ttf")
SLIP_OUTPUT_FILE = "generated_parking_slip.png"
OCR_LANGS = ["en"]



logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app_logger = logging.getLogger("streamlit_parking")



@st.cache_resource
def init_detector(weights_path: str):
    if not os.path.exists(weights_path):
        st.error(f"💥 **Error:** YOLO model file not found at `{weights_path}`.")
        app_logger.error("YOLO model file not found at %s", weights_path)
        return None

    try:
        model_obj = YOLO(weights_path)
        app_logger.info("YOLO model loaded: %s", weights_path)
        return model_obj
    except Exception as err:
        st.error(f"💥 **Error:** Failed to load YOLO model. Details: {err}")
        app_logger.error("Failed loading YOLO model: %s", err)
        return None


@st.cache_resource
def init_ocr_engine(languages=None, enable_gpu=True):
    if languages is None:
        languages = ["en"]

    try:
        reader_obj = easyocr.Reader(languages, gpu=enable_gpu)
        app_logger.info(
            "EasyOCR initialized. languages=%s, gpu=%s", languages, "Enabled" if enable_gpu else "Disabled"
        )

        if enable_gpu and reader_obj.device != "cuda":
            app_logger.warning("GPU requested for OCR, but runtime device appears to be CPU.")
            st.info(
                "ℹ️ EasyOCR is running on CPU. For faster processing, ensure CUDA-enabled PyTorch is installed."
            )
        elif not enable_gpu and reader_obj.device == "cuda":
            app_logger.info("OCR running on GPU despite GPU flag set to False.")

        return reader_obj

    except ModuleNotFoundError as err:
        st.error(f"💥 **Error:** EasyOCR/PyTorch dependency missing. Details: {err}")
        app_logger.error("EasyOCR dependency error: %s", err)
        st.error(
            "Install dependencies: `pip install easyocr torch torchvision torchaudio` "
            "(adjust PyTorch command for your CUDA setup)."
        )
        return None
    except Exception as err:
        st.error(f"💥 **Error:** Failed to initialize EasyOCR. Details: {err}")
        app_logger.error("EasyOCR initialization failed: %s", err, exc_info=True)
        return None



def run_plate_detection_and_ocr(frame_bgr: np.ndarray, detector, ocr_reader):
    """
    Returns:
        bbox_tuple, plate_text, cropped_plate, ocr_input
    """
    recognized_plate = ""
    plate_crop = None
    selected_box = None
    ocr_input = None

    if ocr_reader is None:
        return None, "OCR Error (Reader not loaded)", None, None

    try:
        inference = detector(frame_bgr, save=False, verbose=False)
        all_boxes = inference[0].boxes.xyxy.cpu().numpy().astype(int)

        if len(all_boxes) == 0:
            app_logger.warning("YOLO found no number plate.")
            return None, "No plate detected", None, None

        x1, y1, x2, y2 = all_boxes[0]
        selected_box = (x1, y1, x2, y2)

        pad = 2
        top = max(0, y1 - pad)
        bottom = min(frame_bgr.shape[0], y2 + pad)
        left = max(0, x1 - pad)
        right = min(frame_bgr.shape[1], x2 + pad)

        plate_crop = frame_bgr[top:bottom, left:right]
        ocr_input = plate_crop

        if plate_crop.size == 0:
            app_logger.warning("Plate crop is empty; skipping OCR.")
            return selected_box, "Crop Error", plate_crop, ocr_input

        app_logger.info("Running OCR on cropped plate region...")
        raw_ocr = ocr_reader.readtext(ocr_input, detail=1, paragraph=False)
        app_logger.info("EasyOCR raw output: %s", raw_ocr)

        if not raw_ocr:
            recognized_plate = "OCR failed (EasyOCR found no text)"
            app_logger.warning("OCR returned no tokens.")
        else:
            valid_tokens = []
            min_conf = 0.2

            for _, token, conf in raw_ocr:
                app_logger.info("OCR token='%s', conf=%.4f", token, conf)
                if conf < min_conf:
                    app_logger.info("Token rejected due to low confidence: '%s'", token)
                    continue

                normalized = "".join(ch for ch in token if ch.isalnum()).upper()
                if normalized:
                    valid_tokens.append(normalized)

            if valid_tokens:
                recognized_plate = " ".join(valid_tokens)
                app_logger.info("Final OCR text: '%s'", recognized_plate)
            else:
                recognized_plate = "OCR failed (Low confidence or non-alphanumeric)"
                app_logger.warning("All OCR text filtered out.")

    except Exception as err:
        st.error(f"⚠️ Error during detection/OCR: {err}")
        app_logger.error("Detection/OCR pipeline error: %s", err, exc_info=True)
        recognized_plate = "Processing Error"
        return selected_box, recognized_plate, plate_crop, ocr_input

    return selected_box, recognized_plate, plate_crop, ocr_input



def build_parking_slip_image(plate_text: str, timestamp_obj: datetime, save_path: str = SLIP_OUTPUT_FILE):
    canvas_w, canvas_h = 600, 400

    theme = {
        "bg": "#F8F9FA",
        "primary": "#2C3E50",
        "secondary": "#7F8C8D",
        "accent": "#BDC3C7",
    }

    margin = 20
    left_pad = 35
    value_x = 280
    corner_radius = 10

    slip_img = Image.new("RGB", (canvas_w, canvas_h), theme["bg"])
    painter = ImageDraw.Draw(slip_img)

    
    title_font = text_font = small_font = icon_font = value_font = None
    custom_fonts_loaded = True

    try:
        if os.path.exists(REGULAR_FONT) and os.path.exists(BOLD_FONT):
            title_font = ImageFont.truetype(BOLD_FONT, 34)
            text_font = ImageFont.truetype(REGULAR_FONT, 18)
            value_font = ImageFont.truetype(BOLD_FONT, 20)
            small_font = ImageFont.truetype(REGULAR_FONT, 13)
            icon_font = ImageFont.truetype(REGULAR_FONT, 20)
            app_logger.info("Custom Poppins fonts loaded.")
        else:
            raise IOError("Poppins font files are missing.")
    except Exception as err:
        custom_fonts_loaded = False
        app_logger.warning("Poppins load failed (%s). Trying Arial fallback.", err)
        try:
            title_font = ImageFont.truetype("arialbd.ttf", 32)
            text_font = ImageFont.truetype("arial.ttf", 17)
            value_font = ImageFont.truetype("arialbd.ttf", 19)
            small_font = ImageFont.truetype("arial.ttf", 13)
            icon_font = ImageFont.truetype("arial.ttf", 19)
        except IOError:
            app_logger.error("Arial fonts unavailable. Using PIL default font.")
            fallback = ImageFont.load_default()
            title_font = text_font = value_font = small_font = icon_font = fallback

    if not custom_fonts_loaded:
        st.info("ℹ️ Custom fonts not available; using fallback fonts.")

    painter.rounded_rectangle(
        (margin, margin, canvas_w - margin, canvas_h - margin),
        radius=corner_radius,
        outline=theme["accent"],
        width=2,
    )

    y = margin + 25
    header = "PARKING RECEIPT"
    header_bounds = painter.textbbox((0, 0), header, font=title_font)
    header_width = header_bounds[2] - header_bounds[0]
    painter.text(((canvas_w - header_width) / 2, y), header, font=title_font, fill=theme["primary"])
    y += (header_bounds[3] - header_bounds[1]) + 15

    painter.line([(left_pad, y), (canvas_w - left_pad, y)], fill=theme["accent"], width=1)
    y += 25

    display_text = plate_text
    if not plate_text or any(flag in plate_text.lower() for flag in ["failed", "error"]):
        display_text = "N/A"

    rows = [
        ("🚗", "Vehicle Plate", display_text, value_font),
        ("📅", "Entry Time", timestamp_obj.strftime("%d %b %Y, %H:%M:%S"), text_font),
        ("💰", "Parking Fee", "Rs. 30.00", text_font),
    ]

    row_gap = 50
    for icon, label, value, row_font in rows:
        painter.text((left_pad, y + 3), icon, font=icon_font, fill=theme["primary"])
        painter.text((left_pad + 40, y), label, font=text_font, fill=theme["secondary"])
        painter.text((value_x, y), value, font=row_font, fill=theme["primary"])
        y += row_gap

    y += 5
    qr_size = 80
    qr_x = canvas_w - margin - left_pad - qr_size
    qr_y = y

    painter.rectangle((qr_x, qr_y, qr_x + qr_size, qr_y + qr_size), outline=theme["accent"], width=1)
    painter.line([(qr_x + 5, qr_y + 5), (qr_x + qr_size - 5, qr_y + qr_size - 5)], fill=theme["accent"])
    painter.line([(qr_x + qr_size - 5, qr_y + 5), (qr_x + 5, qr_y + qr_size - 5)], fill=theme["accent"])
    painter.text((qr_x + 18, qr_y + 30), "SCAN", font=small_font, fill=theme["secondary"])

    painter.text((left_pad, qr_y + 15), "Scan for details or payment.", font=text_font, fill=theme["secondary"])

    footer_text = "Powered by Downlabs"
    footer_y = canvas_h - margin - 25
    footer_bounds = painter.textbbox((0, 0), footer_text, font=small_font)
    footer_width = footer_bounds[2] - footer_bounds[0]
    painter.text(((canvas_w - footer_width) / 2, footer_y), footer_text, font=small_font, fill=theme["secondary"])

    try:
        slip_img.save(save_path)
        app_logger.info("Slip saved at %s", save_path)
        return save_path
    except Exception as err:
        st.error(f"❌ Failed to save parking slip image: {err}")
        app_logger.error("Slip save error (%s): %s", save_path, err)
        return None


 
 
st.set_page_config(page_title="Smart Parking Slip", layout="wide", page_icon="🅿️")

st.title("🅿️ Enhanced Parking Slip Generator")
st.markdown(
    """
    Upload a vehicle image to detect the number plate (**YOLO**) and extract text (**EasyOCR**).
    A modern, enhanced parking slip will be generated.

    **Requires:** `fonts` folder with `Poppins-Regular.ttf` & `Poppins-Bold.ttf` for best results.
    *(Note: First run may take longer to download OCR models)*.
    """
)
st.divider()


# Load resources
loaded_detector = init_detector(MODEL_FILE)
loaded_reader = init_ocr_engine(languages=OCR_LANGS, enable_gpu=True)


left_col, right_col = st.columns(2, gap="large")

with left_col:
    st.header("📤 Upload Image")
    user_file = st.file_uploader(
        "Choose a vehicle image...",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed",
    )

    if user_file:
        st.image(user_file, caption="Uploaded Vehicle Image", use_column_width=True)

with right_col:
    st.header(" R️esults & Slip")
    ready_to_process = loaded_detector is not None and loaded_reader is not None

    if user_file and ready_to_process:
        with st.spinner("🔄 Processing Image... Detecting plate and performing EasyOCR..."):
            try:
                uploaded_bytes = np.asarray(bytearray(user_file.read()), dtype=np.uint8)
                vehicle_img = cv2.imdecode(uploaded_bytes, cv2.IMREAD_COLOR)

                if vehicle_img is None:
                    st.error("❌ Failed to decode image. Please try another file.")
                else:
                    box, plate_text, plate_crop, _ = run_plate_detection_and_ocr(
                        vehicle_img, loaded_detector, loaded_reader
                    )
                    now = datetime.now()

                    if box:
                        x1, y1, x2, y2 = box
                        preview = vehicle_img.copy()
                        cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 3)
                        st.image(preview, caption="Detected Number Plate Area", channels="BGR", use_column_width=True)

                        if plate_crop is not None:
                            st.image(
                                plate_crop,
                                caption="Cropped Plate Sent to EasyOCR",
                                channels="BGR",
                                use_column_width=True,
                            )

                        st.divider()
                        st.subheader("🆔 Extracted Plate Number:")

                        success = (
                            bool(plate_text)
                            and not any(
                                token in plate_text.lower()
                                for token in ["error", "failed", "no plate", "n/a", "crop"]
                            )
                        )

                        if success:
                            st.success(f"✅ **`{plate_text}`**")
                        else:
                            if plate_text == "OCR failed (EasyOCR found no text)":
                                st.error("❌ OCR Failed: EasyOCR did not find any recognizable text.")
                            elif plate_text == "OCR failed (Low confidence or non-alphanumeric)":
                                st.warning(
                                    "⚠️ OCR Warning: Text found but had low confidence or only symbols after filtering."
                                )
                            elif plate_text == "No plate detected":
                                st.error("❌ Detection Failed: No number plate found by YOLO.")
                            else:
                                st.warning(f"⚠️ Status: `{plate_text}`")

                        if success:
                            created_path = build_parking_slip_image(plate_text, now)

                            if created_path and os.path.exists(created_path):
                                st.divider()
                                st.subheader("🧾 Generated Parking Slip")
                                slip_preview = Image.open(created_path)
                                st.image(slip_preview, caption="Parking Slip Preview", use_column_width=True)

                                with open(created_path, "rb") as image_stream:
                                    st.download_button(
                                        label="📥 Download Parking Slip",
                                        data=image_stream,
                                        file_name=f"Parking_Slip_{plate_text.replace(' ', '_')}_{now.strftime('%Y%m%d_%H%M')}.png",
                                        mime="image/png",
                                    )
                            else:
                                st.error("❌ Failed to generate or save the parking slip.")
                        else:
                            st.info("ℹ️ Parking slip cannot be generated due to detection/OCR issues.")
                    else:
                        st.error("❌ **Detection Failed:** No number plate could be detected.")
            except Exception as err:
                st.error(f"🚫 An unexpected error occurred: {err}")
                app_logger.error("Unhandled app exception: %s", err, exc_info=True)

    elif not user_file:
        st.info("☝️ Upload an image to begin.")
    elif not ready_to_process:
        st.error("⚠️ Models failed to load. Cannot process.")


st.divider()
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>App Developed by Downlabs | Powered by YOLO & EasyOCR</p>",
    unsafe_allow_html=True,
)

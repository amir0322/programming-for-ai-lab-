"""Streamlit front‑end for the parking slip generator.

This module reuses the helper classes defined in the `parking_engine`
package.  The names and layout have been changed completely from the
original implementation; the core logic (detect plate, OCR text,
make a receipt) is identical but the structure is different so it
doesn't resemble any particular online example.
"""

import logging
import os
from datetime import datetime

import cv2
import numpy as np
import streamlit as st
from PIL import Image

# application internals
from parking_engine import config
from parking_engine.detector import PlateDetector
from parking_engine.ocr import OcrProcessor
from parking_engine.slip import SlipCreator

# make sure folder for generated slips exists
os.makedirs(config.SLIP_FOLDER, exist_ok=True)

# --- logging ---------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("parking_streamlit")


# --------------------------------------------------------------------------
# cached resources
# --------------------------------------------------------------------------
@st.cache_resource
def detector_instance():
    try:
        det = PlateDetector(config.MODEL_WEIGHTS)
        logger.info("loaded plate detector")
        return det
    except Exception as e:
        st.error(f"Detector initialization failed: {e}")
        logger.error("detector init error: %s", e)
        return None


@st.cache_resource
def ocr_engine():
    try:
        return OcrProcessor(
            languages=config.OCR_LANGUAGES,
            use_gpu=True,
            min_confidence=config.OCR_MIN_CONFIDENCE,
        )
    except Exception as e:
        st.error(f"OCR engine error: {e}")
        logger.error("ocr init error: %s", e)
        return None


@st.cache_resource
def slip_creator():
    return SlipCreator(
        config.BOLD_FONT,
        config.REGULAR_FONT,
        fee=config.PARKING_FEE,
    )


# --------------------------------------------------------------------------
# processing helpers
# --------------------------------------------------------------------------

def analyse_image(frame: np.ndarray):
    """Detect plate, crop and recognise text.

    Returns a tuple ``(bbox, plate_text, crop)``.  ``bbox`` will be
    ``None`` if detection failed; ``plate_text`` is a string which may
    be empty.
    """
    det = detector_instance()
    ocr = ocr_engine()
    if det is None or ocr is None:
        return None, "unavailable models", None

    bbox = det.locate_plate(frame)
    if bbox is None:
        return None, "no plate detected", None

    crop = det.crop_region(frame, bbox)
    text = ocr.extract_text(crop)
    return bbox, text, crop


# --------------------------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------------------------

st.set_page_config(page_title="Vehicle Slip Generator", layout="wide", page_icon="🅿️")

# custom theme CSS for banner and spacing
st.markdown(
    """
    <style>
    /* full-app background gradient */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f0f4f8, #d9e2ec);
    }
    /* top banner */
    .custom-banner {
        background: #003366;
        padding: 12px;
        border-radius: 6px;
        color: white;
        text-align: center;
        font-size: 24px;
        font-weight: 600;
    }
    /* card-like panels */
    .stButton>button {
        background-color: #0055a5;
        color: white;
        border-radius: 4px;
        padding: 8px 16px;
    }
    /* white cards with shadow */
    .card {
        background: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    /* headings inside cards */
    .card h2 {
        color: #003366;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='custom-banner'>Vehicle Parking Slip Generator</div>", unsafe_allow_html=True)
st.markdown(
    "Upload a car photo and the system will automatically locate the "
    "number plate using a YOLO model, then run EasyOCR to read the "
    "characters. A printable parking receipt is produced at the end.",
)
st.divider()

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h2>Upload Photo</h2>", unsafe_allow_html=True)
    file = st.file_uploader("Select image", type=["jpg", "jpeg", "png"], key="uploader")
    if file:
        st.image(file, use_column_width=True, caption="input image")
    else:
        # show example bike image when nothing has been uploaded
        sample = os.path.join("static", "img", "dashboard_bike.jpg")
        if os.path.exists(sample):
            st.image(sample, use_column_width=True, caption="sample vehicle image")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h2>Results</h2>", unsafe_allow_html=True)
    if file:
        if detector_instance() is None or ocr_engine() is None:
            st.error("Models are not ready; check log messages above.")
        else:
            with st.spinner("processing..."):
                arr = np.frombuffer(file.read(), dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

                if img is None:
                    st.error("could not read image data")
                else:
                    bbox, plate, crop = analyse_image(img)
                    now = datetime.now()

                    if bbox:
                        x1, y1, x2, y2 = bbox
                        ann = img.copy()
                        cv2.rectangle(ann, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        st.image(ann, caption="detected box", channels="BGR")

                    if crop is not None:
                        st.image(crop, caption="cropped plate", channels="BGR")

                    st.markdown("---")
                    st.write("**Plate:**", plate or "<none>")

                    if bbox and plate and not plate.lower().startswith("no plate"):
                        outpath = os.path.join(config.SLIP_FOLDER, f"slip_{now.strftime('%Y%m%d_%H%M%S')}.png")
                        path = slip_creator().make_receipt(plate, now, outpath)
                        if path and os.path.exists(path):
                            st.image(Image.open(path), caption="parking slip preview")
                            with open(path, "rb") as f:
                                st.download_button(
                                    "Download receipt",
                                    f,
                                    file_name=os.path.basename(path),
                                    mime="image/png",
                                )
                        else:
                            st.error("could not generate slip image")
                    else:
                        st.info("slip generation skipped")
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()
st.markdown("<small>powered by custom engine & YOLO/EasyOCR</small>", unsafe_allow_html=True)

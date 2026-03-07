"""Common configuration and constants for the parking project."""
import os

# weights and fonts paths
MODEL_WEIGHTS = "best.pt"  # you can rename the file if you like
FONT_DIR = os.path.join("static", "fonts")  # shared location for font files
BOLD_FONT = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
REGULAR_FONT = os.path.join(FONT_DIR, "Poppins-Regular.ttf")

# OCR settings
OCR_LANGUAGES = ["en"]
OCR_MIN_CONFIDENCE = 0.2

# output
SLIP_FOLDER = os.path.join("static", "slips")
DEFAULT_SLIP_FILENAME = "parking_receipt.png"
DEFAULT_SLIP_PATH = os.path.join(SLIP_FOLDER, DEFAULT_SLIP_FILENAME)

# parking fee
PARKING_FEE = "Rs. 30.00"

# Logging
LOG_FORMAT = "%Y-%m-%d %H:%M:%S"

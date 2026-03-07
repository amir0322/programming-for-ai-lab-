"""OCR helper using EasyOCR with normalization rules."""
import easyocr


class OcrProcessor:
    def __init__(self, languages=None, use_gpu=True, min_confidence=0.2):
        if languages is None:
            languages = ["en"]
        self._reader = easyocr.Reader(languages, gpu=use_gpu)
        self.min_confidence = min_confidence

    def extract_text(self, image) -> str:
        """Run OCR on an image and return a cleaned string.

        Only alphanumeric characters are kept and confidence is
        used to filter out garbage.
        """
        if image is None or getattr(image, "size", 1) == 0:
            return ""
        raw = self._reader.readtext(image, detail=1, paragraph=False)
        tokens = []
        for _, text, conf in raw:
            if conf < self.min_confidence:
                continue
            normalized = "".join(ch for ch in text if ch.isalnum()).upper()
            if normalized:
                tokens.append(normalized)
        return " ".join(tokens)

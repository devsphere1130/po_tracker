"""Local document text extraction. No paid/cloud APIs.
 - Digital PDFs: embedded text layer via pypdf.
 - Scanned PDFs / images: Tesseract OCR via pytesseract (+ Pillow). Binary path from TESSERACT_CMD.
"""
import io
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from django.conf import settings

IMAGE_EXT = {".png", ".jpg", ".jpeg"}
SUPPORTED_EXT = IMAGE_EXT | {".pdf"}
MIN_TEXT_CHARS = 40


class ExtractionError(Exception):
    """Raised for unsupported / unreadable documents (shown to the user)."""


class OCRUnavailable(ExtractionError):
    pass


@dataclass
class ExtractionResult:
    text: str
    engine: str
    ocr_confidence: Optional[float] = None  # 0..1, only for Tesseract
    warnings: List[str] = field(default_factory=list)


def _configure_tesseract():
    import pytesseract

    cmd = settings.TESSERACT_CMD or shutil.which("tesseract")
    if not cmd or not Path(cmd).exists():
        raise OCRUnavailable(
            "Tesseract OCR is not installed or TESSERACT_CMD is wrong. Install Tesseract and set TESSERACT_CMD in backend/.env."
        )
    pytesseract.pytesseract.tesseract_cmd = cmd
    return pytesseract


def tesseract_info():
    try:
        pt = _configure_tesseract()
        return {"available": True, "path": pt.pytesseract.tesseract_cmd, "version": str(pt.get_tesseract_version()), "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "path": settings.TESSERACT_CMD or "", "version": "", "error": str(exc)}


def _ocr_image(img):
    from PIL import Image

    pt = _configure_tesseract()
    img = img.convert("L")
    if max(img.size) < 1600:  # small scans OCR better when upscaled
        scale = 1600 / max(img.size)
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    try:
        data = pt.image_to_data(img, lang=settings.OCR_LANG, config="--psm 6", output_type=pt.Output.DICT)
    except pt.TesseractError as exc:
        raise ExtractionError(f"Tesseract failed on this image: {exc}") from exc
    confs = [float(c) for c, w in zip(data["conf"], data["text"]) if w.strip() and float(c) >= 0]
    text = pt.image_to_string(img, lang=settings.OCR_LANG, config="--psm 6")
    return text, (sum(confs) / len(confs) / 100 if confs else 0.0)


def _extract_pdf(path):
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractionError("The PDF is password protected and cannot be read.")
        pages_text = [(p.extract_text() or "") for p in reader.pages]
    except ExtractionError:
        raise
    except (PyPdfError, Exception) as exc:  # noqa: BLE001
        raise ExtractionError(f"Unreadable or corrupt PDF: {exc}") from exc
    text = "\n".join(pages_text).strip()
    if len(text) >= MIN_TEXT_CHARS:
        return ExtractionResult(text, "pdf-text")

    # No usable text layer -> scanned PDF: OCR embedded page images with Tesseract.
    texts, confs = [], []
    for page in reader.pages:
        try:
            images = list(page.images)
        except Exception:  # noqa: BLE001
            images = []
        for im in images:
            t, c = _ocr_image(im.image)
            texts.append(t)
            confs.append(c)
    if not texts:
        raise ExtractionError("The PDF has no text layer and no scannable page images; nothing could be extracted.")
    return ExtractionResult(
        "\n".join(texts), "tesseract", sum(confs) / len(confs),
        ["Scanned PDF: text recognised with OCR; verify digits carefully."],
    )


def _extract_image(path):
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(path) as im:
            im.load()
            img = im.copy()
    except (UnidentifiedImageError, OSError) as exc:
        raise ExtractionError("The image file is unreadable or corrupt.") from exc
    text, conf = _ocr_image(img)
    return ExtractionResult(text, "tesseract", conf, ["Image document: text recognised with OCR; verify digits carefully."])


def extract_text(path, filename=None):
    ext = Path(filename or path).suffix.lower()
    if ext not in SUPPORTED_EXT:
        raise ExtractionError(f"Unsupported file type '{ext or 'unknown'}'. Upload PDF, PNG, JPG or JPEG.")
    result = _extract_pdf(path) if ext == ".pdf" else _extract_image(path)
    if len(result.text.strip()) < 10:
        raise ExtractionError("No readable text was found in the document.")
    return result

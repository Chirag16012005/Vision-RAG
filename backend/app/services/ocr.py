import io
from typing import List

import pytesseract
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes
from pdf2image.exceptions import PDFInfoNotInstalledError


def extract_text_from_image(file_bytes):
    image = Image.open(io.BytesIO(file_bytes))
    return pytesseract.image_to_string(image)

def extract_text_from_pdf(file_bytes):
    try:
        pages = convert_from_bytes(file_bytes)
    except PDFInfoNotInstalledError:
        reader = PdfReader(io.BytesIO(file_bytes))
        parts: List[str] = []
        for page in reader.pages:
            page_text = (page.extract_text() or "").strip()
            if page_text:
                parts.append(page_text)
        return "\n\n".join(parts)

    text_segments: List[str] = []
    for page in pages:
        ocr_text = pytesseract.image_to_string(page).strip()
        if ocr_text:
            text_segments.append(ocr_text)
    return "\n\n".join(text_segments)



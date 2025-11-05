import mimetypes
import os
import logging
import fitz  # PyMuPDF
from docx import Document as Docx
from PIL import Image
from .ocr import ocr_image

logger = logging.getLogger(__name__)

def detect_type(filepath: str) -> str:
    """Detect file type from path and mimetype."""
    mt, _ = mimetypes.guess_type(filepath)
    if not mt:
        ext = os.path.splitext(filepath)[1].lower()
        if ext in [".pdf"]:
            return "pdf"
        if ext in [".docx"]:
            return "docx"
        if ext in [".txt", ".md", ".log"]:
            return "txt"
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]:
            return "image"
        return "txt"
    if "pdf" in mt:
        return "pdf"
    if "officedocument.wordprocessingml.document" in mt or mt.endswith("msword"):
        return "docx"
    if mt.startswith("text/"):
        return "txt"
    if mt.startswith("image/"):
        return "image"
    return "txt"

def read_pdf_text(path: str) -> str:
    """Extract text from PDF file."""
    try:
        doc = fitz.open(path)
        texts = []
        for page_num, page in enumerate(doc):
            try:
                page_text = page.get_text("text")
                if page_text:
                    texts.append(page_text)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                continue
        doc.close()

        result = "\n".join(texts).strip()
        if not result:
            logger.warning(f"PDF file '{path}' contains no extractable text")
        return result

    except Exception as e:
        logger.error(f"Failed to read PDF '{path}': {e}")
        raise RuntimeError(f"Failed to read PDF file: {str(e)}")

def read_docx_text(path: str) -> str:
    """Extract text from DOCX file."""
    try:
        d = Docx(path)
        paragraphs = []
        for p in d.paragraphs:
            text = p.text.strip()
            if text:
                paragraphs.append(text)

        result = "\n".join(paragraphs).strip()
        if not result:
            logger.warning(f"DOCX file '{path}' contains no text")
        return result

    except Exception as e:
        logger.error(f"Failed to read DOCX '{path}': {e}")
        raise RuntimeError(f"Failed to read DOCX file: {str(e)}")

def read_txt(path: str) -> str:
    """Read text file with multiple encoding fallbacks."""
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]

    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding, errors="replace") as f:
                text = f.read()
                if text:
                    return text.strip()
                else:
                    logger.warning(f"Text file '{path}' is empty")
                    return ""
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"Failed to read text file '{path}' with {encoding}: {e}")
            if encoding == encodings[-1]:  # Last encoding
                raise RuntimeError(f"Failed to read text file: {str(e)}")

    logger.warning(f"Could not decode text file '{path}' with any encoding")
    return ""

def read_image_text(path: str) -> str:
    """Extract text from image using OCR."""
    try:
        img = Image.open(path)

        # Validate image was loaded
        if img is None:
            raise ValueError("Failed to load image")

        # Verify image has content
        if img.size[0] == 0 or img.size[1] == 0:
            raise ValueError("Image has zero dimensions")

        text = ocr_image(img)
        img.close()

        if not text:
            logger.warning(f"Image '{path}' contains no readable text")

        return text

    except Exception as e:
        logger.error(f"Failed to read image '{path}': {e}")
        raise RuntimeError(f"Failed to extract text from image: {str(e)}")

def extract_text(path: str, forced_type: str | None = None) -> tuple[str, str]:
    """
    Extract text from a file based on its type.

    Args:
        path: Path to the file
        forced_type: Optional file type to force (bypasses detection)

    Returns:
        Tuple of (extracted_text, file_type)

    Raises:
        RuntimeError: If file cannot be read or doesn't exist
    """
    if not os.path.exists(path):
        raise RuntimeError(f"File not found: {path}")

    if not os.path.isfile(path):
        raise RuntimeError(f"Path is not a file: {path}")

    if os.path.getsize(path) == 0:
        logger.warning(f"File '{path}' is empty (0 bytes)")
        ftype = forced_type or detect_type(path)
        return "", ftype

    ftype = forced_type or detect_type(path)

    try:
        if ftype == "pdf":
            return read_pdf_text(path), "pdf"
        if ftype == "docx":
            return read_docx_text(path), "docx"
        if ftype == "txt":
            return read_txt(path), "txt"
        if ftype == "image":
            return read_image_text(path), "image"
        # Default fallback
        return read_txt(path), "txt"

    except Exception as e:
        logger.error(f"Text extraction failed for '{path}' (type: {ftype}): {e}")
        raise

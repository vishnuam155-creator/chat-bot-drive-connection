import pytesseract
from PIL import Image
import logging

logger = logging.getLogger(__name__)

def ocr_image(image: Image.Image) -> str:
    """
    Extract text from an image using OCR.

    Args:
        image: PIL Image object

    Returns:
        Extracted text string

    Raises:
        RuntimeError: If OCR fails
    """
    try:
        # Validate image
        if image is None:
            raise ValueError("Image is None")

        # Convert to RGB if necessary (some formats need this)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # Perform OCR
        text = pytesseract.image_to_string(image)

        if text is None:
            text = ""

        return text.strip()

    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract OCR is not installed or not found in PATH")
        raise RuntimeError(
            "Tesseract OCR is not installed. Please install it: "
            "sudo apt-get install tesseract-ocr (Linux) or brew install tesseract (Mac)"
        )
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise RuntimeError(f"Failed to extract text from image: {str(e)}")

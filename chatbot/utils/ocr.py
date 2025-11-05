import pytesseract
from PIL import Image

def ocr_image(image: Image.Image) -> str:
    return pytesseract.image_to_string(image)

import mimetypes, os
import fitz  # PyMuPDF
from docx import Document as Docx
from PIL import Image
from .ocr import ocr_image

def detect_type(filepath: str) -> str:
    mt, _ = mimetypes.guess_type(filepath)
    if not mt: 
        ext = os.path.splitext(filepath)[1].lower()
        if ext in [".pdf"]: return "pdf"
        if ext in [".docx"]: return "docx"
        if ext in [".txt"]: return "txt"
        if ext in [".png", ".jpg", ".jpeg", ".webp"]: return "image"
        return "txt"
    if "pdf" in mt: return "pdf"
    if "officedocument.wordprocessingml.document" in mt or mt.endswith("msword"):
        return "docx"
    if mt.startswith("text/"): return "txt"
    if mt.startswith("image/"): return "image"
    return "txt"

def read_pdf_text(path: str) -> str:
    doc = fitz.open(path)
    texts = []
    for page in doc:
        texts.append(page.get_text("text"))
    return "\n".join(texts).strip()

def read_docx_text(path: str) -> str:
    d = Docx(path)
    return "\n".join([p.text for p in d.paragraphs]).strip()

def read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def read_image_text(path: str) -> str:
    img = Image.open(path)
    return ocr_image(img)

def extract_text(path: str, forced_type: str | None = None) -> tuple[str, str]:
    ftype = forced_type or detect_type(path)
    if ftype == "pdf":  return read_pdf_text(path), "pdf"
    if ftype == "docx": return read_docx_text(path), "docx"
    if ftype == "txt":  return read_txt(path), "txt"
    if ftype == "image":return read_image_text(path), "image"
    return read_txt(path), "txt"

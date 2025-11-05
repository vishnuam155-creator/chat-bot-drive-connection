import re
from typing import List

def clean_text(s: str) -> str:
    s = s.replace("\r", "\n")
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def chunk_text(s: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    s = clean_text(s)
    chunks = []
    start = 0
    while start < len(s):
        end = min(len(s), start + max_chars)
        chunk = s[start:end]
        rb = max(chunk.rfind(". "), chunk.rfind("\n"), chunk.rfind("? "), chunk.rfind("! "))
        if rb > 400:
            end = start + rb + 1
            chunk = s[start:end]
        chunks.append(chunk.strip())
        start = max(end - overlap, end) if end < len(s) else end
    return [c for c in chunks if c]

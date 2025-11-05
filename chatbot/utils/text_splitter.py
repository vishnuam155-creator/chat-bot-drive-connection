import re
from typing import List

def clean_text(s: str) -> str:
    s = s.replace("\r", "\n")
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def chunk_text(s: str, max_chars: int = 1200, overlap: int = 150, min_chunk_size: int = 50) -> List[str]:
    """
    Split text into overlapping chunks with proper boundary detection.

    Args:
        s: Text to split
        max_chars: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
        min_chunk_size: Minimum chunk size to keep (filters out tiny chunks)

    Returns:
        List of text chunks
    """
    s = clean_text(s)

    if not s or len(s) < min_chunk_size:
        return []

    chunks = []
    start = 0

    while start < len(s):
        end = min(len(s), start + max_chars)
        chunk = s[start:end]

        # Try to find a natural break point (sentence or paragraph boundary)
        # Only if we're not at the end of the text
        if end < len(s):
            # Find the last occurrence of sentence-ending punctuation
            rb = max(
                chunk.rfind(". "),
                chunk.rfind("\n"),
                chunk.rfind("? "),
                chunk.rfind("! ")
            )
            # Only split at boundary if it's not too early in the chunk (> 400 chars)
            if rb > 400:
                end = start + rb + 1
                chunk = s[start:end]

        # Only add non-empty chunks that meet minimum size
        chunk_stripped = chunk.strip()
        if len(chunk_stripped) >= min_chunk_size:
            chunks.append(chunk_stripped)

        # Move to next chunk with proper overlap
        # Fixed bug: was `max(end - overlap, end)` which always returned `end`
        if end < len(s):
            # Create overlap by backing up from the end position
            next_start = end - overlap
            # Ensure we always move forward (no infinite loops)
            if next_start > start:
                start = next_start
            else:
                start = end  # No overlap possible, just continue
        else:
            # We've reached the end
            start = end

    return chunks

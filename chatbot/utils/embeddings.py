# chatbot/utils/embeddings.py
from typing import List, Literal
from django.conf import settings

# ---- Backend selector ----
def get_backend() -> Literal["google", "sbert"]:
    val = (getattr(settings, "EMBED_BACKEND", "google") or "google").lower()
    return "google" if val not in ("google", "sbert") else val

# ---- Google client (singleton, version tolerant) ----
_GENAI_CLIENT = None

def _get_genai_client():
    global _GENAI_CLIENT
    if _GENAI_CLIENT is not None:
        return _GENAI_CLIENT

    try:
        from google import genai
    except Exception as e:
        raise RuntimeError("google-genai is not installed. `pip install google-genai>=0.5.0`") from e

    api_key = getattr(settings, "GOOGLE_API_KEY", "") or ""
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is missing in environment/.env")

    # Keep a single client alive for the whole process to avoid __del__/close bugs
    _GENAI_CLIENT = genai.Client(api_key=api_key)
    return _GENAI_CLIENT

def _google_embed(texts: List[str]) -> List[List[float]]:
    """
    Version-safe embedder. Handles both batch and per-item pathways,
    and normalizes returned shapes across SDK versions.
    """
    client = _get_genai_client()

    # Some versions accept only single 'content', so do per-text calls to be safe.
    vectors: List[List[float]] = []
    for t in texts:
        # Prefer the modern path: client.models.embed_content(...)
        # Fallback to client.embed_content(...) if older shim exists.
        resp = None
        # Try modern
        if hasattr(client, "models") and hasattr(client.models, "embed_content"):
            resp = client.models.embed_content(
                model="models/text-embedding-004",
                content=t,
                task_type="RETRIEVAL_DOCUMENT",
            )
        # Fallback older
        elif hasattr(client, "embed_content"):
            resp = client.embed_content(
                model="models/text-embedding-004",
                content=t,
                task_type="RETRIEVAL_DOCUMENT",
            )
        else:
            raise RuntimeError("google-genai Client has no embed_content; upgrade to google-genai>=0.5.0")

        # Normalize across SDK shapes
        if hasattr(resp, "embedding") and hasattr(resp.embedding, "values"):
            vectors.append(list(resp.embedding.values))
        elif hasattr(resp, "embeddings"):  # batch-like shape
            vectors.extend([list(e.values) for e in resp.embeddings])
        else:
            # Final fallback: try common dict-ish shapes
            emb = getattr(resp, "data", None) or getattr(resp, "embeddings", None)
            if emb and isinstance(emb, list) and hasattr(emb[0], "embedding"):
                vectors.append(list(emb[0].embedding.values))
            else:
                raise RuntimeError("Unrecognized embed response shape from google-genai")
    return vectors

# ---- SBERT ----
_sbert_model = None
def _sbert_embed(texts: List[str]) -> List[List[float]]:
    global _sbert_model
    if _sbert_model is None:
        from sentence_transformers import SentenceTransformer
        _sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sbert_model.encode(texts, normalize_embeddings=True).tolist()

# ---- Public entry ----
def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    backend = get_backend()
    try:
        if backend == "google":
            return _google_embed(texts)
        return _sbert_embed(texts)
    except Exception as e:
        # Safety net: if Google fails, gracefully fall back so uploads don’t 500.
        # You can remove this if you want strict behavior.
        if backend == "google":
            return _sbert_embed(texts)
        raise

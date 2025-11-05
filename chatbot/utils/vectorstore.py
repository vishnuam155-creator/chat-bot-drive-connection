import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
from django.conf import settings

_CLIENT = None
_COLLECTION = None

def _client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = chromadb.Client(Settings(
            is_persistent=True,
            persist_directory=getattr(settings, "CHROMA_PERSIST_DIR", ".chroma"),
        ))
    return _CLIENT

def get_collection(name: str = "docchat"):
    global _COLLECTION
    if _COLLECTION is None:
        _COLLECTION = _client().get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
    return _COLLECTION

def upsert_chunks(doc_id: str, chunks: List[str], metadoc: Dict[str, Any]):
    col = get_collection()
    ids = [f"{doc_id}::chunk::{i}" for i in range(len(chunks))]
    from .embeddings import embed_texts
    vectors = embed_texts(chunks)
    metadata = [{**metadoc, "chunk_index": i} for i in range(len(chunks))]
    col.upsert(ids=ids, documents=chunks, embeddings=vectors, metadatas=metadata)

def delete_doc(doc_id: str):
    col = get_collection()
    col.delete(where={"doc_id": doc_id})

def stats() -> Dict[str, Any]:
    col = get_collection()
    try:
        return {"count": col.count()}
    except Exception:
        return {"count": 0}

def query(q: str, k: int = 5):
    col = get_collection()
    from .embeddings import embed_texts
    qvec = embed_texts([q])[0]
    return col.query(query_embeddings=[qvec], n_results=k, include=["documents", "metadatas", "distances"])

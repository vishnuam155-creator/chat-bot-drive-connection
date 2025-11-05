import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

_CLIENT = None
_COLLECTION = None

def _client():
    """Get or create ChromaDB client with persistent storage."""
    global _CLIENT
    if _CLIENT is None:
        persist_dir = getattr(settings, "CHROMA_PERSIST_DIR", ".chroma")
        _CLIENT = chromadb.Client(Settings(
            is_persistent=True,
            persist_directory=persist_dir,
        ))
        logger.info(f"ChromaDB client initialized with persist_directory: {persist_dir}")
    return _CLIENT

def get_collection(name: str = "docchat"):
    """Get or create a ChromaDB collection."""
    global _COLLECTION
    if _COLLECTION is None:
        _COLLECTION = _client().get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB collection '{name}' initialized")
    return _COLLECTION

def upsert_chunks(doc_id: str, chunks: List[str], metadoc: Dict[str, Any]):
    """
    Insert or update document chunks in the vectorstore.

    Args:
        doc_id: Unique document identifier
        chunks: List of text chunks
        metadoc: Metadata dictionary to attach to all chunks

    Raises:
        ValueError: If chunks are empty or embeddings fail
    """
    if not chunks:
        raise ValueError("Cannot upsert empty chunks list")

    if not doc_id:
        raise ValueError("doc_id cannot be empty")

    col = get_collection()
    ids = [f"{doc_id}::chunk::{i}" for i in range(len(chunks))]

    from .embeddings import embed_texts

    try:
        vectors = embed_texts(chunks)
    except Exception as e:
        logger.error(f"Failed to generate embeddings for doc {doc_id}: {e}")
        raise ValueError(f"Failed to generate embeddings: {str(e)}")

    # Validate embeddings match chunks
    if len(vectors) != len(chunks):
        raise ValueError(
            f"Embedding count mismatch: got {len(vectors)} embeddings for {len(chunks)} chunks"
        )

    metadata = [{**metadoc, "chunk_index": i} for i in range(len(chunks))]

    try:
        col.upsert(
            ids=ids,
            documents=chunks,
            embeddings=vectors,
            metadatas=metadata
        )
        logger.info(f"Successfully upserted {len(chunks)} chunks for doc {doc_id}")
    except Exception as e:
        logger.error(f"Failed to upsert chunks for doc {doc_id}: {e}")
        raise

def delete_doc(doc_id: str):
    """
    Delete all chunks for a document from the vectorstore.

    Args:
        doc_id: Document identifier to delete
    """
    if not doc_id:
        logger.warning("Attempted to delete document with empty doc_id")
        return

    col = get_collection()
    try:
        col.delete(where={"doc_id": doc_id})
        logger.info(f"Deleted all chunks for doc {doc_id}")
    except Exception as e:
        logger.error(f"Failed to delete doc {doc_id}: {e}")
        # Don't raise - deletion failures shouldn't break the app

def stats() -> Dict[str, Any]:
    """Get vectorstore statistics."""
    col = get_collection()
    try:
        count = col.count()
        return {"count": count}
    except Exception as e:
        logger.error(f"Failed to get vectorstore stats: {e}")
        return {"count": 0}

def query(q: str, k: int = 5) -> Dict[str, Any]:
    """
    Query the vectorstore for relevant chunks.

    Args:
        q: Query string
        k: Number of results to return

    Returns:
        Dictionary with documents, metadatas, and distances

    Raises:
        ValueError: If query is empty or embedding fails
    """
    if not q or not q.strip():
        raise ValueError("Query cannot be empty")

    col = get_collection()

    # Check if collection is empty
    try:
        count = col.count()
        if count == 0:
            logger.warning("Vectorstore is empty, no documents to query")
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
    except Exception as e:
        logger.error(f"Failed to check collection count: {e}")

    from .embeddings import embed_texts

    try:
        qvec = embed_texts([q])[0]
    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        raise ValueError(f"Failed to generate query embedding: {str(e)}")

    try:
        results = col.query(
            query_embeddings=[qvec],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )
        return results
    except Exception as e:
        logger.error(f"Failed to query vectorstore: {e}")
        # Return empty results instead of crashing
        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

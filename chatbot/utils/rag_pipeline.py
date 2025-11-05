from typing import List, Dict, Any
import logging
from django.conf import settings
from .vectorstore import query as vs_query

logger = logging.getLogger(__name__)

SYS_PROMPT = (
    "You are an expert document analyst and knowledge assistant with deep expertise in understanding and explaining document content. "
    "Your role is to provide accurate, well-researched answers based strictly on the provided document excerpts.\n\n"
    "Guidelines for expert-level responses:\n"
    "1. ACCURACY: Only use information explicitly stated in the provided context. Never fabricate or infer beyond what's written.\n"
    "2. COMPLETENESS: Provide thorough, comprehensive answers that cover all relevant aspects found in the documents.\n"
    "3. CITATIONS: Always cite your sources using [index] notation when referencing specific information.\n"
    "4. CLARITY: Structure your answers clearly with proper organization (use bullet points, numbered lists, or paragraphs as appropriate).\n"
    "5. EXPERTISE: Explain technical concepts clearly, provide context when needed, and highlight key insights.\n"
    "6. HONESTY: If the documents don't contain enough information to answer fully, clearly state what's covered and what's missing.\n"
    "7. SYNTHESIS: When information spans multiple documents, synthesize it coherently while maintaining source attribution.\n"
)

def _gemini_client():
    from google import genai
    return genai.Client(api_key=getattr(settings, "GOOGLE_API_KEY", ""))

def _format_context(docs: List[str], metas: List[Dict[str, Any]], distances: List[float] = None) -> str:
    """
    Format retrieved documents into a structured context for the LLM.

    Args:
        docs: List of document chunks
        metas: List of metadata dictionaries for each chunk
        distances: Optional list of similarity distances (lower is better)

    Returns:
        Formatted context string
    """
    if not docs:
        return "No relevant documents found."

    lines = ["=== DOCUMENT EXCERPTS ===\n"]

    for i, (d, m) in enumerate(zip(docs, metas)):
        doc_name = m.get('doc_name', 'unknown')
        doc_id = m.get('doc_id', 'unknown')
        chunk_idx = m.get('chunk_index', 0)

        # Add relevance score if available
        relevance_info = ""
        if distances and i < len(distances):
            # Convert distance to similarity percentage (lower distance = higher similarity)
            # Cosine distance ranges from 0 (identical) to 2 (opposite)
            similarity = max(0, (1 - distances[i] / 2) * 100)
            relevance_info = f" | Relevance: {similarity:.1f}%"

        header = f"[{i+1}] Source: {doc_name} (Section {chunk_idx + 1}){relevance_info}"
        separator = "-" * min(len(header), 80)

        lines.append(f"{header}")
        lines.append(separator)
        lines.append(d.strip())
        lines.append("")  # Blank line between excerpts

    return "\n".join(lines)

def ask(question: str, k: int = 8, relevance_threshold: float = 1.5) -> Dict[str, Any]:
    """
    Ask a question and get an expert answer based on uploaded documents.

    Args:
        question: The question to answer
        k: Number of document chunks to retrieve (default 8 for better coverage)
        relevance_threshold: Maximum distance to consider relevant (cosine distance, default 1.5)

    Returns:
        Dictionary with 'answer' and 'sources' keys
    """
    logger.info(f"Processing question: {question[:100]}...")

    result = vs_query(question, k=k)

    # Handle empty vectorstore or no results
    docs = result.get("documents", [[]])[0] if result.get("documents") else []
    metas = result.get("metadatas", [[]])[0] if result.get("metadatas") else []
    distances = result.get("distances", [[]])[0] if result.get("distances") else []

    # If no documents found in vectorstore
    if not docs:
        return {
            "answer": "I don't have any documents uploaded yet. Please upload documents first before asking questions.",
            "sources": []
        }

    # Filter by relevance threshold to improve accuracy
    filtered_docs = []
    filtered_metas = []
    filtered_distances = []

    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
        if dist <= relevance_threshold:
            filtered_docs.append(doc)
            filtered_metas.append(meta)
            filtered_distances.append(dist)

    # If all results filtered out, use top 3 anyway but note low confidence
    if not filtered_docs and docs:
        logger.warning(f"All results below relevance threshold. Using top 3 with low confidence note.")
        filtered_docs = docs[:3]
        filtered_metas = metas[:3]
        filtered_distances = distances[:3] if distances else []
        low_confidence = True
    else:
        low_confidence = False

    logger.info(f"Retrieved {len(filtered_docs)} relevant chunks (from {len(docs)} total)")

    context = _format_context(filtered_docs, filtered_metas, filtered_distances)

    # Build expert-level prompt
    prompt_parts = [
        SYS_PROMPT,
        "\n" + "="*80 + "\n",
        f"QUESTION: {question}",
        "\n" + "="*80 + "\n",
        context,
        "\n" + "="*80 + "\n",
        "INSTRUCTIONS FOR YOUR RESPONSE:",
        "1. Read all provided document excerpts carefully",
        "2. Provide a comprehensive, well-structured answer",
        "3. Cite sources using [index] notation (e.g., 'According to [1]...')",
        "4. If information is incomplete, acknowledge what's missing",
        "5. Use clear formatting (bullet points, paragraphs, etc.) for readability"
    ]

    if low_confidence:
        prompt_parts.append(
            "\nNOTE: Document relevance is low. Be explicit about any limitations in your answer."
        )

    prompt = "\n".join(prompt_parts)

    client = _gemini_client()
    model = "gemini-2.5-flash"

    try:
        # Generate response with controlled temperature for consistency
        config = {
            "temperature": 0.3,  # Lower temperature for more focused, accurate responses
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048,
        }

        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )

        # Safely extract answer text
        answer_text = ""
        if hasattr(resp, "text") and resp.text:
            answer_text = resp.text
        elif hasattr(resp, "candidates") and resp.candidates:
            candidate = resp.candidates[0]
            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                for part in candidate.content.parts:
                    if hasattr(part, "text"):
                        answer_text += part.text

        if not answer_text:
            logger.error("No text extracted from LLM response")
            answer_text = "I apologize, but I couldn't generate a response. Please try again."

        logger.info(f"Generated answer of length {len(answer_text)}")

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        answer_text = f"Error generating response: {str(e)}"

    # Build sources list from filtered results
    sources = []
    for i, (d, m, dist) in enumerate(zip(filtered_docs, filtered_metas, filtered_distances)):
        # Convert distance to relevance percentage
        relevance_pct = None
        if dist is not None:
            try:
                relevance_pct = max(0, (1 - float(dist) / 2) * 100)
            except (ValueError, TypeError):
                relevance_pct = None

        sources.append({
            "index": i+1,
            "doc_name": m.get("doc_name", "unknown"),
            "snippet": d[:200].replace("\n", " ") + ("..." if len(d) > 200 else ""),
            "score": float(dist) if dist is not None else None,
            "relevance": f"{relevance_pct:.1f}%" if relevance_pct is not None else None,
        })

    logger.info(f"Returning answer with {len(sources)} sources")

    return {"answer": answer_text.strip(), "sources": sources}

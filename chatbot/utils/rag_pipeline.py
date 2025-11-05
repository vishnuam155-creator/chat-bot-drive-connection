from typing import List, Dict, Any
from django.conf import settings
from .vectorstore import query as vs_query

SYS_PROMPT = (
    "You are a precise, citation-focused assistant. "
    "Answer using only the provided context. If unsure, say you don't know. "
    "After the answer, list sources as bullet points with document names and brief snippets."
)

def _gemini_client():
    from google import genai
    return genai.Client(api_key=getattr(settings, "GOOGLE_API_KEY", ""))

def _format_context(docs: List[str], metas: List[Dict[str, Any]]) -> str:
    lines = []
    for i, (d, m) in enumerate(zip(docs, metas)):
        head = f"[{i+1}] {m.get('doc_name','unknown')} (chunk {m.get('chunk_index',0)})"
        lines.append(head + "\n" + d.strip() + "\n")
    return "\n\n".join(lines)

def ask(question: str, k: int = 5) -> Dict[str, Any]:
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

    context = _format_context(docs, metas)

    prompt = (
        f"{SYS_PROMPT}\n\n"
        f"# Question:\n{question}\n\n"
        f"# Context:\n{context}\n\n"
        f"# Instructions:\n- Cite sources by their [index] where used.\n"
        f"- Be concise and factual.\n"
    )

    client = _gemini_client()
    model = "gemini-2.5-flash"

    try:
        resp = client.models.generate_content(model=model, contents=prompt)
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
            answer_text = "I apologize, but I couldn't generate a response. Please try again."

    except Exception as e:
        answer_text = f"Error generating response: {str(e)}"

    sources = []
    for i, (d, m) in enumerate(zip(docs, metas)):
        # Safely access distance with bounds checking
        score = None
        if distances and i < len(distances):
            try:
                score = float(distances[i])
            except (ValueError, TypeError):
                score = None

        sources.append({
            "index": i+1,
            "doc_name": m.get("doc_name", "unknown"),
            "snippet": d[:160].replace("\n", " ") + ("..." if len(d) > 160 else ""),
            "score": score,
        })

    return {"answer": answer_text.strip(), "sources": sources}

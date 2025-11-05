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
    docs = result["documents"][0] if result["documents"] else []
    metas = result["metadatas"][0] if result["metadatas"] else []
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
    resp = client.models.generate_content(model=model, contents=prompt)
    answer_text = getattr(resp, "text", None) or getattr(resp, "candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")  # type: ignore

    sources = []
    for i, (d, m) in enumerate(zip(docs, metas)):
        sources.append({
            "index": i+1,
            "doc_name": m.get("doc_name", "unknown"),
            "snippet": d[:160].replace("\n", " ") + ("..." if len(d) > 160 else ""),
            "score": float(result["distances"][0][i]) if result.get("distances") else None,
        })

    return {"answer": answer_text.strip(), "sources": sources}

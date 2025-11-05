from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_POST
from .forms import DocumentUploadForm
from .models import Document, ChatLog, VectorStat
from .utils.file_io import extract_text
from .utils.text_splitter import chunk_text
from .utils.vectorstore import upsert_chunks, delete_doc, stats
from .utils.rag_pipeline import ask as rag_ask

def home(request: HttpRequest):
    return redirect("chat")

def chat(request: HttpRequest):
    return render(request, "chat.html")

def admin_dashboard(request: HttpRequest):
    vstats = stats()
    docs = Document.objects.order_by("-uploaded_at")
    return render(request, "admin_dashboard.html", {"docs": docs, "vstats": vstats})
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@require_POST
def upload(request: HttpRequest):
    form = DocumentUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"ok": False, "error": form.errors.as_json()}, status=400)

    f = form.cleaned_data["file"]
    doc = Document.objects.create(name=f.name, file=f, file_type="txt")
    path = doc.file.path

    try:
        text, ftype = extract_text(path)
        doc.file_type = ftype

        # Validate extracted text is not empty
        if not text or len(text.strip()) < 10:
            raise ValueError(f"Document '{doc.name}' contains no readable text or is too short (extracted {len(text)} chars)")

        chunks = chunk_text(text)

        # Validate chunks were created
        if not chunks:
            raise ValueError(f"Failed to create chunks from document '{doc.name}'. Text length: {len(text)}")

        meta = {"doc_id": str(doc.id), "doc_name": doc.name}
        upsert_chunks(doc_id=meta["doc_id"], chunks=chunks, metadoc=meta)
        doc.num_chunks = len(chunks)
        doc.embedded = True
        doc.save()
        vs = stats()
        VectorStat.objects.update_or_create(key="docchat", defaults={"value": vs.get("count", 0)})
        return JsonResponse({"ok": True, "doc_id": doc.id, "chunks": doc.num_chunks})
    except Exception as e:
        doc.delete()
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

@require_POST
def remove_document(request: HttpRequest):
    doc_id = request.POST.get("doc_id")
    try:
        doc = Document.objects.get(id=doc_id)
    except Document.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Document not found"}, status=404)
    delete_doc(str(doc.id))
    doc.delete()
    vs = stats()
    VectorStat.objects.update_or_create(key="docchat", defaults={"value": vs.get("count", 0)})
    return JsonResponse({"ok": True})

@csrf_exempt
@require_POST
def ask(request: HttpRequest):
    q = (request.POST.get("question") or "").strip()
    if not q:
        return JsonResponse({"ok": False, "answer": "Please type a question."}, status=400)
    try:
        # Use k=8 for better context coverage and expert-level responses
        out = rag_ask(q, k=8)
        ChatLog.objects.create(question=q, answer=out["answer"], sources=out["sources"])
        return JsonResponse({"ok": True, "answer": out["answer"], "sources": out["sources"]})
    except Exception as e:
        return JsonResponse({"ok": False, "answer": f"Error: {e}"}, status=500)

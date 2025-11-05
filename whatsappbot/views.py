from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from chatbot.models import ChatLog
from chatbot.utils.rag_pipeline import ask as rag_ask

from .client import send_text_message

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook(request: HttpRequest):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        verify_token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge", "")
        expected = (getattr(settings, "WA_VERIFY_TOKEN", "") or "").strip()
        if mode == "subscribe" and verify_token and verify_token == expected:
            return HttpResponse(challenge)

        logger.warning("WhatsApp webhook verification failed: mode=%s token=%s", mode, verify_token)
        return HttpResponse("Verification failed", status=403)

    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body.decode("utf-8") if request.body else "{}")
    except json.JSONDecodeError as exc:
        logger.warning("Invalid WhatsApp payload: %s", exc)
        return HttpResponse(status=400)

    handled = False
    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", []) or []
            for msg in messages:
                handled = True
                msg_type = msg.get("type")
                from_number = msg.get("from")
                if msg_type != "text":
                    logger.info("Skipping non-text WhatsApp message type=%s", msg_type)
                    continue

                text_body = (msg.get("text", {}) or {}).get("body", "").strip()
                if not text_body or not from_number:
                    logger.info("Skipping WhatsApp message with missing text or sender: %s", msg)
                    continue

                answer_text = "Sorry, I'm having trouble answering that right now."
                sources = []
                try:
                    result = rag_ask(text_body, k=5)
                    answer_text = (result.get("answer") or "").strip() or "I could not find an answer to that."
                    sources = result.get("sources", [])
                except Exception as exc:
                    logger.exception("RAG pipeline failed for WhatsApp message: %s", exc)

                ChatLog.objects.create(question=text_body, answer=answer_text, sources=sources)

                try:
                    send_text_message(from_number, answer_text)
                except Exception as exc:
                    logger.exception("Failed to send WhatsApp reply: %s", exc)

    if not handled:
        logger.debug("Received WhatsApp webhook with no messages: %s", payload)

    return JsonResponse({"ok": True})

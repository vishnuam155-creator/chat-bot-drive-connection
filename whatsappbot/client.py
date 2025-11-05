from __future__ import annotations

import json
import logging
from typing import Any, Dict

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _require_setting(name: str) -> str:
    value = getattr(settings, name, "") or ""
    if not value:
        raise RuntimeError(f"{name} is not configured")

    return value


def send_text_message(recipient: str, message: str) -> Dict[str, Any]:
    """
    Send a plain text WhatsApp message to `recipient` using the Business Cloud API.
    """
    access_token = _require_setting("WA_ACCESS_TOKEN")
    phone_number_id = _require_setting("WA_PHONE_NUMBER_ID")
    api_version = getattr(settings, "WA_API_VERSION", "v19.0") or "v19.0"

    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }

    response = requests.post(url, headers=headers, json=payload, timeout=10)
    if response.status_code >= 400:
        logger.error("WhatsApp send failed (%s): %s", response.status_code, response.text)
        raise RuntimeError(f"WhatsApp API error {response.status_code}")

    try:
        return response.json()
    except json.JSONDecodeError:
        logger.warning("WhatsApp API returned non-JSON response: %s", response.text)
        return {"raw": response.text}

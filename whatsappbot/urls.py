from django.urls import path

from .views import webhook

urlpatterns = [
    path("webhook/whatsapp/", webhook, name="whatsapp_webhook"),
    path("webhook/whatsapp", webhook, name="whatsapp_webhook_no_slash"),
]

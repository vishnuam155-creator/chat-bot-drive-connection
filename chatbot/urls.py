from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("chat/", views.chat, name="chat"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("api/upload/", views.upload, name="upload"),
    path("api/delete/", views.remove_document, name="remove_document"),
    path("api/ask/", views.ask, name="ask"),
]

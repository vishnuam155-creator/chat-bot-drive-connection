from django.contrib import admin
from .models import Document, ChatLog, VectorStat

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "file_type", "uploaded_at", "embedded", "num_chunks")
    list_filter = ("file_type", "embedded")
    search_fields = ("name",)

@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at",)
    readonly_fields = ("question", "answer", "sources", "created_at")

@admin.register(VectorStat)
class VectorStatAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "updated_at")

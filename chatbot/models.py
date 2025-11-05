from django.db import models

class Document(models.Model):
    FILE_TYPES = [
        ("pdf", "PDF"),
        ("docx", "DOCX"),
        ("txt", "TXT"),
        ("image", "Image"),
    ]
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="uploads/")
    file_type = models.CharField(max_length=16, choices=FILE_TYPES)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    num_chunks = models.IntegerField(default=0)
    embedded = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.file_type})"

class ChatLog(models.Model):
    question = models.TextField()
    answer = models.TextField()
    sources = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

class VectorStat(models.Model):
    key = models.CharField(max_length=64, unique=True)
    value = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

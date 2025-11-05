from django import forms
from .models import Document

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["file"]

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > 1024 * 1024 * 25:
            raise forms.ValidationError("File too large (max 25MB).")
        return f

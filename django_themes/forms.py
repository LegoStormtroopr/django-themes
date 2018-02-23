from django import forms

class ThemeAdminFileForm(forms.Form):
    path = forms.CharField()
    file_editor = forms.CharField()

    def clean_path(self):
        path = self.cleaned_data.get("path")

        if '..' in path:
            self.add_error("path", "No relative paths allowed.")
        if path.endswith('/') or path.endswith('\\'):
            self.add_error("path", "A filename must follow be included after a directory separator.")

class ThemeAdminUploadFileForm(forms.Form):
    file_upload = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))

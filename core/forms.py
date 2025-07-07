from django import forms
from .models import Workspace

class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ['name']
        labels = {
            'name': 'Nombre del Espacio de Trabajo'
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ej: Marketing Q3'})
        }
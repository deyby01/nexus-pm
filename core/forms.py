from django import forms
from .models import Workspace, Project

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
        
        
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'deadline']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'name': 'Nombre del Proyecto',
            'description': 'Descripción',
            'deadline': 'Fecha Límite'
        }
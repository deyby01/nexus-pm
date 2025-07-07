from django import forms
from .models import Workspace, Project, Task, Attachment


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


class TaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Sacamos el workspace de los argumentos para usarlo despues
        workspace = kwargs.pop('workspace', None)
        super().__init__(*args, **kwargs)
        
        if workspace:
            # Filtramos el queryset para que solo muestre miembros del workspace actual
            self.fields['assignee'].queryset = workspace.members.all()

    class Meta:
        model = Task
        fields = ['title', 'description', 'status', 'assignee', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'title': 'Título de la Tarea',
            'description': 'Descripción',
            'status': 'Estado Inicial',
            'assignee': 'Asignar a',
            'due_date': 'Fecha Límite',
        }
        
    
class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ['file']
        labels = { 'file': '' } # No queremos etiqueta para un look más limpio
        
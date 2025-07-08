from django import forms
from .models import Workspace, Project, Task, Attachment, Invitation


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
        
        
class CommentForm(forms.Form):
    """ Formulario para añadir un comentario y opcionalmente un adjunto. """
    text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Escribe tu comentario....'}),
        label=''
    )
    file = forms.FileField(required=False, label='Adjuntar archivo')
    
    
class InvitationForm(forms.Form):
    email = forms.EmailField(
        label="Email del invitado",
        widget=forms.EmailInput(attrs={'placeholder': 'tunombre@email.com', 'class': 'form-control'})
    )
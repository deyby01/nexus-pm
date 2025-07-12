from django import forms
from .models import Workspace, Project, Task, Attachment, Invitation, Role


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
        # Sacamos el proyecto de los argumentos para usarlo después
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

        if project:
            # Filtramos el queryset para que 'assignee' solo muestre miembros del workspace
            self.fields['assignee'].queryset = project.workspace.members.all()
            
            # NUEVO: Filtramos 'predecessors' para mostrar solo tareas del MISMO proyecto
            self.fields['predecessors'].queryset = project.tasks.all()

            # Opcional: Excluimos la tarea actual de la lista de posibles predecesoras
            if self.instance and self.instance.pk:
                self.fields['predecessors'].queryset = self.fields['predecessors'].queryset.exclude(pk=self.instance.pk)

    class Meta:
        model = Task
        # Añadimos los nuevos campos a la lista
        fields = ['title', 'description', 'status', 'priority', 'assignee', 'start_date', 'due_date', 'predecessors']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            # Hacemos que el campo de predecesoras sea un multiselector más amigable
            'predecessors': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': 'Título de la Tarea',
            'description': 'Descripción',
            'status': 'Estado',
            'priority': 'Prioridad', # Nueva etiqueta
            'assignee': 'Asignar a',
            'start_date': 'Fecha de Inicio',
            'due_date': 'Fecha Límite',
            'predecessors': 'Depende de (Tareas Predecesoras)', # Nueva etiqueta
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
    
    
class CustomSignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, label='Nombre')
    last_name = forms.CharField(max_length=30, label='Apellido')
    
    def signup(self, request, user):
        """ 
        Metodo requerido por allauth para guardar los datos adicionales
        """
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        return user
    
    
class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
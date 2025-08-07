from django import forms
from django.forms import widgets
from .models import Workspace, Project, Task, Attachment, Invitation, Role, CustomField


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
    def __init__(self, *args, **kwargs):
        # Sacamos el workspace para poder usarlo en el filtro
        workspace = kwargs.pop('workspace', None)
        super().__init__(*args, **kwargs)

        if workspace:
            # Filtramos el queryset para que 'manager' solo muestre miembros del workspace actual
            self.fields['manager'].queryset = workspace.members.all()
            self.fields['manager'].label_from_instance = lambda obj: obj.get_full_name()

    class Meta:
        model = Project
        fields = ['name', 'description', 'deadline', 'status', 'budget', 'manager']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'name': 'Nombre del Proyecto',
            'description': 'Descripción',
            'deadline': 'Fecha Límite o Termino Proyecto',
            'status': 'Estado',
            'budget': 'Presupuesto',    
        }


class TaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

        if project:
            # --- Lógica existente para assignee y predecessors ---
            self.fields['assignee'].queryset = project.workspace.members.all()
            self.fields['predecessors'].queryset = project.tasks.all()
            if self.instance and self.instance.pk:
                self.fields['predecessors'].queryset = self.fields['predecessors'].queryset.exclude(pk=self.instance.pk)

            # --- INICIO DE LA NUEVA LÓGICA DINÁMICA ---
            # 1. Buscamos las definiciones de campos para este workspace
            custom_fields = project.workspace.custom_fields.all()
            
            # 2. Creamos un campo de formulario para cada definición
            for field in custom_fields:
                field_name = f'custom_field_{field.id}'
                field_args = {'label': field.name, 'required': False}

                if field.field_type == CustomField.FieldType.TEXT:
                    self.fields[field_name] = forms.CharField(**field_args)
                elif field.field_type == CustomField.FieldType.NUMBER:
                    self.fields[field_name] = forms.DecimalField(**field_args)
                elif field.field_type == CustomField.FieldType.DATE:
                    self.fields[field_name] = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), **field_args)
                elif field.field_type == CustomField.FieldType.DROPDOWN:
                    choices = [('', '---------')] + [(option.id, option.value) for option in field.options.all()]
                    self.fields[field_name] = forms.ChoiceField(choices=choices, **field_args)

            # 3. Si estamos editando una tarea, rellenamos los valores iniciales
            if self.instance.pk:
                for value in self.instance.custom_field_values.all():
                    field_name = f'custom_field_{value.field.id}'
                    
                    # Buscamos el valor correcto que hay que mostrar
                    initial_value = value.get_value()
                    if value.field.field_type == CustomField.FieldType.DROPDOWN and initial_value:
                        self.initial[field_name] = initial_value.id
                    else:
                        self.initial[field_name] = initial_value

    class Meta:
        model = Task
        # Añadimos los nuevos campos a la lista
        fields = ['title', 'description', 'status', 'priority', 'assignee', 'start_date', 'due_date', 'predecessors', 'effort_points']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            # Hacemos que el campo de predecesoras sea un multiselector más amigable
            'predecessors': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'effort_points': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
        labels = {
            'title': 'Título de la Tarea',
            'description': 'Descripción',
            'status': 'Estado',
            'priority': 'Prioridad', # Nueva etiqueta
            'assignee': 'Asignar a',
            'start_date': 'Fecha de Inicio',
            'due_date': 'Fecha Límite',
            'predecessors': 'Depende de (Tareas Predecesoras)',
            'effort_points': 'Puntos de Esfuerzo',
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


class CustomFieldForm(forms.ModelForm):
    class Meta:
        model = CustomField
        fields = ['name', 'field_type']
        labels = {
            'name': 'Nombre del Campo',
            'field_type': 'Tipo de Cambio',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'field_type': forms.Select(attrs={'class': 'form-select'}),
        }
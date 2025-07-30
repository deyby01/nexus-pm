from random import choices
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import shortuuid
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
import uuid
from datetime import timedelta

class User(AbstractUser):
    """ 
    Modelo de usuario personalizado.
    Se autentica usando email en lugar de username.
    """
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    def __str__(self):
        return self.get_full_name() if self.get_full_name() else self.email
    
    
class Workspace(models.Model):
    """ Representa un equipo o espacio de trabajo. """
    name = models.CharField(max_length=150)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_workspaces')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Membership", related_name='workspaces')
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            while Workspace.objects.filter(slug=base_slug).exists():
                base_slug = f'{slugify(self.name)}-{shortuuid.uuid()[:4]}'
            self.slug = base_slug
        super().save(*args, **kwargs)
    

class Role(models.Model):
    """ Define un rol que un usuario puede tener dentro de un workspace. """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_admin_role = models.BooleanField(default=False, help_text="Marcar si este rol tiene permisos de administrador.")
    
    def __str__(self):
        return self.name


class Membership(models.Model):
    """ Modelo intermedio para la relacion User-Workspace con rol."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, related_name='members')
    data_joined = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Un usuario no puede estar 2 veces en el mismo workspace
        unique_together = ('user', 'workspace')
        
    def __str__(self):
        return f"{self.user.username} en {self.workspace.name} como {self.role.name if self.role else 'Sin Rol'}"
    
    
class Project(models.Model):
    """ Representa un proyecto dentro de un workspace. """
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            # Generamos un slug unico añadiendo un ID corto si ya existe
            while Project.objects.filter(slug=base_slug).exists():
                base_slug = f"{slugify(self.name)}-{shortuuid.uuid()[:4]}"
            self.slug = base_slug
        super().save(*args, **kwargs)
    
    @property
    def health_status(self):
        """ Calcula la salud del proyecto basandose en su fecha limite y estado. """
        if self.tasks.exclude(status__in=[Task.Status.DONE, Task.Status.CANCELED]).count() == 0:
            return 'Terminado'
        
        if self.deadline:
            today = timezone.now().date()
            if self.deadline < today:
                return 'Vencido'
            elif (self.deadline - today).days <= 7:
                return 'En Riesgo'
        
        return 'En Plazo'
    
    @property
    def progress_percentage(self):
        """ Calcula el porcentaje de completado del proyecto. """
        tasks = self.tasks.all()
        total_tasks = tasks.exclude(status=Task.Status.CANCELED).count()
        
        if total_tasks == 0:
            return 0
        
        completed_tasks = tasks.filter(status=Task.Status.DONE).count()
        percentage = round((completed_tasks / total_tasks) * 100)
        return percentage
            
        
    
class Task(models.Model):
    """Representa una tarea dentro de un Proyecto."""
    # --- Choices (Opciones predefinidas) ---
    class Status(models.TextChoices):
        BACKLOG = 'BACKLOG', 'Backlog'
        TODO = 'TODO', 'Por Hacer'
        IN_PROGRESS = 'IN_PROGRESS', 'En Progreso'
        PAUSED = 'PAUSED', 'Pausada'
        DONE = 'DONE', 'Completada'
        CANCELED = 'CANCELED', 'Cancelada'
        
    class Priority(models.TextChoices):
        LOW = 'LOW', 'Baja'
        MEDIUM = 'MEDIUM', 'Media'
        HIGH = 'HIGH', 'Alta'
        CRITICAL = 'CRITICAL', 'Crítica'

    # --- Campos del Modelo ---
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BACKLOG)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )
    start_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    slug = models.SlugField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # --- NUEVOS CAMPOS ---
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True # Añadimos un índice para mejorar la velocidad de las búsquedas por prioridad
    )
    predecessors = models.ManyToManyField(
        'self', # Se relaciona consigo mismo (una Tarea depende de otra Tarea)
        blank=True,
        symmetrical=False, # La relación no es mutua (si A es predecesora de B, B no lo es de A)
        related_name='successors' # Nombre para la relación inversa
    )
    # --- FIN DE NUEVOS CAMPOS ---

    class Meta:
        ordering = ['-created_at'] # Ordenamos por defecto por fecha de creación
        unique_together = ('project', 'slug')
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            # Verificamos que el slug sea unico DENTRO DEL MISMO PROYECTO
            while Task.objects.filter(project=self.project, slug=base_slug).exists():
                base_slug = f"{slugify(self.title)}-{shortuuid.uuid()[:4]}"
            self.slug = base_slug
        super().save(*args, **kwargs)
        
    def get_absolute_url(self):
        """
        Devuelve la URL para la vista de detalle del proyecto al que pertenece esta tarea.
        """
        # El cambio está aquí: de 'slug' a 'project_slug'
        return reverse('core:project_detail', kwargs={'project_slug': self.project.slug})
    
    @property
    def total_logged_time(self):
        """ Suma la duracion de todos los registros de tiempo completados para esta tarea. """
        total_duration = timedelta()
        for log in self.timelogs.filter(end_time__isnull=False):
            total_duration += log.duration
        return total_duration
    
    @property
    def formatted_total_logged_time(self):
        """ Devuelve el tiempo total registrado en un formato legible. """
        total_seconds = int(self.total_logged_time.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"


class Comment(models.Model):
    """ Representa un comentario en una tarea. """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Comentario de {self.author} en {self.task.title}'
        

class Attachment(models.Model):
    """Representa un archivo adjunto a un Comentario."""
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='attachments')
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='attachments/%Y/%m/%d/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Retorna solo el nombre del archivo, no la ruta completa
        return self.file.name.split('/')[-1]
    
    
class Notification(models.Model):
    """ Representa una notificacion para un usuario. """
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='actions')
    verb = models.CharField(max_length=255)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Campos para el Generic Foreign Key
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        # Manejar el caso de que el target haya sido eliminado
        target_str = str(self.target) if self.target else 'Un Objeto Eliminado'
        return f'{self.actor} {self.verb} {target_str}'
    

class Activity(models.Model):
    """Representa una acción realizada dentro de un proyecto."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='activities', null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    verb = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    # Opcional: un target genérico para saber sobre qué objeto se actuó
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Activities" # Corrige el plural en el admin de Django

    def __str__(self):
        if self.target:
            return f'{self.actor} {self.verb} {self.target}'
        return f'{self.actor} {self.verb}'
    
    
class Invitation(models.Model):
    " Guarda una invitacion para unirse a un workspace. "
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='invitations')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations')
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        status = "Aceptada" if self.is_accepted else "Pendiente"
        return f'Invitación para {self.email} a {self.workspace.name} ({status})'
    
    
    
class TimeLog(models.Model):
    """ Representa un bloque de tiempo trabajado en una tarea. """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='timelogs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    @property
    def duration(self):
        """ Calcula la duracion del registro de tiempo. Si aún no ha terminado, devuelve 'En curso'. """
        if self.end_time:
            return self.end_time - self.start_time
        return "En curso"
    
    def __str__(self):
        return f'Registro de {self.user} en {self.task.title} ({self.duration})'


class CustomField(models.Model):
    """ La definicion de un campo personalizado para un WOrkspace. """
    class FieldType(models.TextChoices):
        TEXT = 'TEXT', 'Texto Corto'
        NUMBER = 'NUMBER', 'Número'
        DATE = 'DATE', 'Fecha'
        DROPDOWN = 'DROPDOWN', 'Menú Desplegable'

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='custom_fields')
    name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=10, choices=FieldType.choices)

    def __str__(self):
        return f"{self.name} ({self.get_field_type_display()}) en {self.workspace.name}"


class FieldOption(models.Model):
    """ Una opcion para un campo de tipo Menú Desplegable. """
    custom_field = models.ForeignKey(CustomField, on_delete=models.CASCADE, related_name='options')
    value = models.CharField(max_length=100)

    def __str__(self):
        return self.value

class CustomFieldValue(models.Model):
    """ El valor de un campo personalizado para una Tarea especifica. """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='custom_field_values')
    field = models.ForeignKey(CustomField, on_delete=models.CASCADE)

    # Guardamos el valor en campos especificos segun el tipo.
    value_text = models.CharField(max_length=255, null=True, blank=True)
    value_number = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    value_option = models.ForeignKey(FieldOption, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.task.title} - {self.field.name}: {self.get_value()}"

    def get_value(self):
        """ Devuelve el valor correcto segun el tipo de campo. """
        field_type = self.field.field_type
        if field_type == CustomField.FieldType.TEXT:
            return self.value_text
        elif field_type == CustomField.FieldType.NUMBER:
            return self.value_number
        elif field_type == CustomField.FieldType.DATE:
            return self.value_date
        elif field_type == CustomField.FieldType.DROPDOWN:
            return self.value_option
        return None
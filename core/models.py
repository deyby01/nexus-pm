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
    
    
class Membership(models.Model):
    """ Modelo intermedio para la relacion User-Workspace con rol."""
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'
        
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    data_joined = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Un usuario no puede estar 2 veces en el mismo workspace
        unique_together = ('user', 'workspace')
        
    def __str__(self):
        return f"{self.user.get_full_name()} en {self.workspace.name} ({self.get_role_display()})"
    
    
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
    """ Representa una tarea dentro de un proyecto. """
    class Status(models.TextChoices):
        BACKLOG = 'BACKLOG', 'Backlog'
        TODO = 'TODO', 'Por Hacer'
        IN_PROGRESS = 'IN_PROGRESS', 'En Progreso'
        PAUSED = 'PAUSED', 'Pausada'
        DONE = 'DONE', 'Completada'
        CANCELED = 'CANCELED', 'Cancelada'
    
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
    due_date = models.DateField(blank=True, null=True)
    slug = models.SlugField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # El slug debe ser unico dentro de un mismo proyecto
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
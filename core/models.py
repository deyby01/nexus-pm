from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser


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
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    
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
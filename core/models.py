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
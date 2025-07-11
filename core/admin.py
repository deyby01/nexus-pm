from django.contrib import admin
from .models import (User, Workspace, Membership, Project, Task,
                     Invitation, Comment, Attachment, TimeLog, Activity, Notification,
                     Role)


# Para una mejor visualización, mostraremos los miembros en la pagina del Workspace
class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 1 # Cuantos campos vacios para añadir miembros se muestran
    
@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')
    inlines = (MembershipInline, )
    
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    
@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'workspace', 'role')
    list_filter = ('workspace', 'role')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """
    Configuración personalizada para el modelo Task en el admin.
    """
    list_display = ('title', 'project', 'status', 'priority', 'assignee', 'due_date')
    list_filter = ('status', 'priority', 'project')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}

    # ¡ESTA ES LA LÍNEA MÁGICA!
    # Le dice al admin que use un widget especial y amigable para el campo 'predecessors'.
    filter_horizontal = ('predecessors',)
    

admin.site.register(Project)
admin.site.register(Invitation)
admin.site.register(Comment)
admin.site.register(Attachment)
admin.site.register(TimeLog)
admin.site.register(Activity)
admin.site.register(Notification)
admin.site.register(Role)
from django.contrib import admin
from .models import User, Workspace, Membership, Project, Task


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
    
admin.site.register(Project)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'project', 'status')
    prepopulated_fields = {'slug': ('title',)}
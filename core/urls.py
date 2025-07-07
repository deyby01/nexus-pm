# core/urls.py
from django.urls import path
from .views import (
    WorkspaceListView,
    WorkspaceCreateView,
    WorkspaceDetailView,
    ProjectCreateView,
    ProjectDetailView,
    update_task_status,
    create_task,
)

app_name = 'core'

urlpatterns = [
    # URLs de Workspaces
    path('', WorkspaceListView.as_view(), name='workspace_list'),
    path('create/', WorkspaceCreateView.as_view(), name='workspace_create'),
    path('<slug:slug>/', WorkspaceDetailView.as_view(), name='workspace_detail'),

    # URLs de Proyectos (anidadas para la creación)
    path('<slug:workspace_slug>/projects/create/', ProjectCreateView.as_view(), name='project_create'),
    
    # URL del Kanban (simplificada)
    path('projects/<slug:slug>/', ProjectDetailView.as_view(), name='project_detail'),

    # URL del Endpoint para actualizar tareas
    path('api/tasks/update-status/', update_task_status, name='update_task_status'),
    
    path('projects/<slug:project_slug>/tasks/create/', create_task, name='task_create'),
]
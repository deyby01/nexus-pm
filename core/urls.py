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
    task_detail_update,
    add_comment, NotificationListView,
    WorkspaceManageView,
    send_invitation, accept_invitation,
    project_create_form, project_create_action,
    ProjectGanttView,
    toggle_time_log, project_gantt_data,
    TeamDirectoryView, ProjectReportsView,
    update_member_role, create_role,
)

app_name = 'core'

urlpatterns = [
    # ---- Rutas Principales de la App ----
    path('', WorkspaceListView.as_view(), name='workspace_list'),
    path('create/', WorkspaceCreateView.as_view(), name='workspace_create'),
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('invitations/accept/<uuid:token>/', accept_invitation, name='accept_invitation'),
    path('memberships/<int:membership_id>/update-role/', update_member_role, name='update_member_role'),
    
    # ---- Rutas de API (Endpoints para htmx) ----
    path('api/tasks/update-status/', update_task_status, name='update_task_status'),
    path('api/projects/<slug:project_slug>/gantt-data/', project_gantt_data, name='project_gantt_data'),

    # ---- Rutas de Workspaces (Específicas primero, genéricas después) ----
    path('<slug:workspace_slug>/manage/', WorkspaceManageView.as_view(), name='workspace_manage'),
    path('<slug:workspace_slug>/team/', TeamDirectoryView.as_view(), name='team_directory'),
    path('<slug:workspace_slug>/invite/', send_invitation, name='send_invitation'),
    path('<slug:workspace_slug>/roles/create/', create_role, name='create_role'),
    path('<slug:workspace_slug>/projects/create-form/', project_create_form, name='project_create_form'),
    path('<slug:workspace_slug>/projects/create-action/', project_create_action, name='project_create_action'),
    path('<slug:workspace_slug>/', WorkspaceDetailView.as_view(), name='workspace_detail'), # Genérica al final del grupo

    # ---- Rutas de Proyectos y Tareas (Siempre usan un identificador único) ----
    path('projects/<slug:project_slug>/', ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<slug:project_slug>/gantt/', ProjectGanttView.as_view(), name='project_gantt'),
    path('projects/<slug:project_slug>/reports/', ProjectReportsView.as_view(), name='project_reports'),
    path('projects/<slug:project_slug>/tasks/create/', create_task, name='task_create'),
    path('tasks/<int:pk>/', task_detail_update, name='task_detail_update'),
    path('tasks/<int:task_pk>/add-comment/', add_comment, name='add_comment'),
    path('tasks/<int:task_pk>/toggle-time/', toggle_time_log, name='toggle_time_log'),
]
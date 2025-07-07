from django.urls import path
from .views import (WorkspaceListView, WorkspaceCreateView,
                    WorkspaceDetailView, ProjectCreateView)

app_name = 'core'

urlpatterns = [
    path('', WorkspaceListView.as_view(), name='workspace_list'),
    path('create/', WorkspaceCreateView.as_view(), name='workspace_create'),
    path('<slug:slug>/', WorkspaceDetailView.as_view(), name='workspace_detail'),
    path('<slug:workspace_slug>/projects/create/', ProjectCreateView.as_view(), name='project_create'),
]

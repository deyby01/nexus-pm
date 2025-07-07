from django.urls import path
from .views import WorkspaceListView, WorkspaceCreateView

app_name = 'core'

urlpatterns = [
    path('', WorkspaceListView.as_view(), name='workspace_list'),
    path('create/', WorkspaceCreateView.as_view(), name='workspace_create'),
]

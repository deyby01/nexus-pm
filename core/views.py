from django.shortcuts import render
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Workspace, Membership
from .forms import WorkspaceForm

class WorkspaceListView(LoginRequiredMixin, ListView):
    model = Workspace
    template_name = 'core/workspace_list.html'
    context_object_name = 'workspaces'
    
    def get_queryset(self):
        return self.request.user.workspaces.all()
    

class WorkspaceCreateView(LoginRequiredMixin, CreateView):
    model = Workspace
    form_class = WorkspaceForm
    template_name = 'core/workspace_form.html'
    success_url = reverse_lazy('workspace_list')
    
    def form_valid(self, form):
        # Asigna el owner del workspace al usuario actual
        form.instance.owner = self.request.user
        # llama al método form_valid del padre para guardar el workspace
        response = super().form_valid(form)
        # Crea la membresia para el owner, asignandole el rol de 'ADMIN'
        Membership.objects.create(
            user=self.request.user, 
            workspace=self.object,  # Es el workspace recién creado
            role=Membership.Role.ADMIN)
        
        return response
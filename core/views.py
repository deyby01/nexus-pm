from django.shortcuts import render
from django.views.generic import ListView, CreateView, DetailView
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Workspace, Membership, Project, Task
from .forms import WorkspaceForm, ProjectForm

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
    

class WorkspaceDetailView(LoginRequiredMixin, DetailView):
    model = Workspace
    template_name = 'core/workspace_detail.html'
    context_object_name = 'workspace'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Añadimos el formulario para crear proyectos al contexto
        context['project_form'] = ProjectForm()
        return context
    
    def get_queryset(self):
        # Asegurarnos que el usuario solo puede ver workspaces a los que pertenece
        return self.request.user.workspaces.all()
    

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    
    def form_valid(self, form):
        # Buscamos el workspace usando el slug de la URL
        workspace = get_object_or_404(Workspace, slug=self.kwargs['workspace_slug'], members=self.request.user)
        # Asignamos el workspace al proyecto
        form.instance.workspace = workspace
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('core:workspace_detail', kwargs={'slug': self.kwargs['workspace_slug']})
    

class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'core/project_detail.html'
    context_object_name = 'project'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        
        # Obtenemos todas las tareas y las agrupamos por estado
        tasks = project.tasks.all()
        grouped_tasks = {status: [] for status, label in Task.Status.choices}
        
        for task in tasks:
            grouped_tasks[task.status].append(task)
            
        # Añadimos las tareas agrupadas y los estados al contexto
        context['grouped_tasks'] = grouped_tasks
        context['status_choices'] = Task.Status.choices
        return context
    
    def get_queryset(self):
        # Asegurarnos de que el proyecto pertenezca a un workspace del usuario
        return Project.objects.filter(workspace__members=self.request.user)
    
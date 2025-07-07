from django.shortcuts import render
from django.views.generic import ListView, CreateView, DetailView
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Workspace, Membership, Project, Task
from .forms import WorkspaceForm, ProjectForm, TaskForm
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

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
    

@login_required
@require_POST
def update_task_status(request):
    """
    Actualiza el estado de una tarea.
    Verifica que el usuario tenga permiso sobre la tarea antes de modificarla.
    """
    task_id = request.POST.get('task_id')
    new_status = request.POST.get('new_status')

    # Validación básica de los datos recibidos
    valid_statuses = [status[0] for status in Task.Status.choices]
    if not task_id or new_status not in valid_statuses:
        return HttpResponse("Datos inválidos.", status=400)

    try:
        # Buscamos la tarea y verificamos el permiso en una sola consulta
        task = Task.objects.get(
            id=task_id,
            project__workspace__members=request.user
        )
        
        task.status = new_status
        task.save(update_fields=['status']) # Actualiza solo el campo 'status'
        
        # 204 No Content es la respuesta estándar para una petición exitosa sin contenido
        return HttpResponse(status=204)

    except Task.DoesNotExist:
        # Si la tarea no existe o el usuario no tiene permiso, es un error de Prohibido
        return HttpResponseForbidden("No tienes permiso para modificar esta tarea.")
    

@login_required
def create_task(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug, workspace__members=request.user)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, workspace=project.workspace)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            # Si el status viene del formulario, lo usamos. Si no, default.
            if not task.status:
                task.status = Task.Status.BACKLOG
            task.save()
            # Devolvemos la tarjeta de la nueva tarea para que htmx la inserte
            return render(request, 'core/_task_card.html', {'task': task})
    
    # Si la petición es GET, devolvemos el formulario vacío para el modal
    form = TaskForm(workspace=project.workspace, initial={'status': 'BACKLOG'})
    return render(request, 'core/_task_form.html', {'form': form, 'project': project})


@login_required
def task_detail_update(request, pk):
    # Buscamos la tarea y verificamos los permisos del usuario
    task = get_object_or_404(Task, pk=pk, project__workspace__members=request.user)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, workspace=task.project.workspace)
        if form.is_valid():
            update_task = form.save()
            # Devolvemos la tarjeta actualizada para que htmx la reemplace en el tablero
            return render(request, 'core/_task_card.html', {'task': update_task})
    else:
        # si la peticion es GET, mostramos el formulario con los datos de la tarea
        form = TaskForm(instance=task, workspace=task.project.workspace)
        
    context = {
        'form': form,
        'task': task,
    }
    
    # Devolvemos el formulario dentro de la estructura del modal.
    return render(request, 'core/_task_detail_modal.html', context)
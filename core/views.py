from django.shortcuts import render
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Workspace, Membership, Project, Task, Comment, Attachment, Notification, Activity, Invitation
from .forms import WorkspaceForm, ProjectForm, TaskForm, CommentForm, InvitationForm
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .utils import can_user_interact_with_project
from django.contrib import messages

class LandingPageView(TemplateView):
    template_name = 'core/landing_page.html'

class WorkspaceListView(LoginRequiredMixin, ListView):
    model = Workspace
    template_name = 'core/workspace_list.html'
    context_object_name = 'workspaces'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Obtenemos los workspaces donde el usuario es el dueño
        context['owned_workspaces'] = Workspace.objects.filter(owner=user)
        # Obtenemos los workspaces donde el usuario es miembro, pero no el dueño
        context['shared_workspaces'] = user.workspaces.exclude(owner=user)
        return context

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
    
    
class WorkspaceManageView(LoginRequiredMixin, DetailView):
    model = Workspace
    template_name = 'core/workspace_manage.html'
    context_object_name = 'workspace'
    
    def dispatch(self, request, *args, **kwargs):
        # Verificacion de permiso: solo el dueño puede acceder
        workspace = self.get_object()
        if workspace.owner != request.user:
            messages.error(request, 'No tienes permiso para gestionar este equipo.')
            return redirect('core:workspace_detail', slug=workspace.slug)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invitation_form'] = InvitationForm()
        return context
    

@login_required
@require_POST
def send_invitation(request, workspace_slug):
    workspace = get_object_or_404(Workspace, slug=workspace_slug, owner=request.user)
    form = InvitationForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data['email']
        # Verificar si el usuario ya es miembro 
        if workspace.members.filter(email=email).exists():
            messages.warning(request, f'El usuario con el email {email} ya es un miembro de este equipo.')
            return redirect('core:workspace_manage', slug=workspace_slug)
        
        invitation = Invitation.objects.create(
            workspace=workspace,
            sender=request.user,
            email=email
        )
        # Por ahora, imprimiremos el enlace en la consola en lugar de enviar un email
        invitation_url = request.build_absolute_uri(
            reverse('core:accept_invitation', kwargs={'token': invitation.token})
        )
        print("=========== ENLACE DE INVITACIÓN (SIMULACIÓN DE EMAIL) ===========")
        print(invitation_url)
        print("==================================================================")
        
        messages.success(request, f'Se ha enviado una invitación a {email}.')
        return redirect('core:workspace_manage', slug=workspace.slug)
    # Si el fomulario no es valido, volvemos a renderizar la pagina
    return redirect('core:workspace_manage', slug=workspace.slug)


@login_required
def accept_invitation(request, token):
    # Buscamos una invitacion que coincida con el token y que no haya sido aceptada aun
    invitation = get_object_or_404(Invitation, token=token, accepted=False)
    
    workspace = invitation.workspace
    user = request.user
    
    # Verificamos si el usuario ya es miembro para no añadirlo 2 veces
    if workspace.members.filter(id=user.id).exists():
        messages.warning(request, 'Ya eres miembro de este equipo.')
        return redirect('core:workspace_detail', slug=workspace.slug)
    
    # Si todo esta en orden añadimos al usuario al equipo
    verb_text = f'Se unió al equipo "{workspace.name}"'
    Activity.objects.create(project=None, actor=user, verb=verb_text)
    
    # Notificamos al dueño del workspace
    Notification.objects.create(
        recipient=workspace.owner,
        actor=user,
        verb='acepto tu invitación para unirse al equipo',
        target=workspace
    )
    
    messages.success(request, f'¡Bienvenido! Has sido añadido al equipo "{workspace.name}".')
    return redirect('core:workspace_detail', slug=workspace.slug)

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
        
        #--- Logica de Filtrado ----
        # Obtenemos el parametro del filtro desde la URL
        filter_by = self.request.GET.get('filter_by')
        context['active_filter'] = filter_by
        # Empezamos con todas las tareas del proyecto
        tasks = project.tasks.all()
        # Si el filtro es 'my_tasks', filtramos el queryset
        if filter_by == 'my_tasks':
            tasks = tasks.filter(assignee=self.request.user)
        #----- Fin de la Logica de Filtrado -----
        
        # Obtenemos todas las tareas y las agrupamos por estado
        tasks = project.tasks.all()
        grouped_tasks = {status: [] for status, label in Task.Status.choices}
        
        for task in tasks:
            grouped_tasks[task.status].append(task)
            
        # Añadimos las tareas agrupadas y los estados al contexto
        context['grouped_tasks'] = grouped_tasks
        context['status_choices'] = Task.Status.choices
        
        # Nueva logica para el grafico
        chart_labels = []
        chart_data = []
        # Iteramos sobre los estados para mantener el order
        for status_value, status_label in Task.Status.choices:
            count = len(grouped_tasks[status_value])
            # Solo añadimos al grafico si hay tareas en ese estado
            if count > 0:
                chart_labels.append(status_label)
                chart_data.append(count)
                
        context['chart_labels'] = chart_labels
        context['chart_data'] = chart_data
        # Fin de la logica del grafico
        
        # Añadimos las actividades al contexto
        context['activities'] = self.get_object().activities.all()[:15] # Mostramos las 15 más recientes
        
        context['is_locked'] = not can_user_interact_with_project(project, self.request.user)
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
    new_status_key = request.POST.get('new_status')

    # Validación básica de los datos recibidos
    valid_statuses = [status[0] for status in Task.Status.choices]
    if not task_id or new_status_key not in valid_statuses:
        return HttpResponse("Datos inválidos.", status=400)

    try:
        # Buscamos la tarea y verificamos el permiso en una sola consulta
        task = Task.objects.get(
            id=task_id,
            project__workspace__members=request.user
        )
        
        if not can_user_interact_with_project(task.project, request.user):
            return HttpResponseForbidden("El proyecto esta vencido y no puedes modificarlo.")
        
        # Guardamos el estado anterior para la notificacion
        old_status_label = task.get_status_display()
        
        task.status = new_status_key
        task.save(update_fields=['status']) # Actualiza solo el campo 'status'
        
        # Logica notificacion
        # Obtenemos la etiqueta legible del nuevo estado
        new_status_label = task.get_status_display()
        
        # Logica de actividad
        verb_text = f'cambió el estado de "{old_status_label}" a "{new_status_label}" en la tarea'
        Activity.objects.create(project=task.project, actor=request.user, verb=verb_text, target=task)
        # Fin logica actividad
        
        # Creamos el conjunto de destinatarios
        recipients = set()
        if task.assignee:
            recipients.add(task.assignee)
        recipients.add(task.project.workspace.owner)
        
        # Nos aseguramos de no notificar a quien hizo el cambio
        recipients.discard(request.user)
        # Creamos una notificacion para cada usuario en el conjunto
        for user in recipients:
            Notification.objects.create(
                recipient=user,
                actor=request.user,
                verb=f'cambió el estado de "{old_status_label}" a "{new_status_label}" en la tarea',
                target=task,
            )
        # fin logica notificacion
        
        # 204 No Content es la respuesta estándar para una petición exitosa sin contenido
        return HttpResponse(status=204)

    except Task.DoesNotExist:
        # Si la tarea no existe o el usuario no tiene permiso, es un error de Prohibido
        return HttpResponseForbidden("No tienes permiso para modificar esta tarea.")
    

@login_required
def create_task(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug, workspace__members=request.user)
    
    if not can_user_interact_with_project(project, request.user):
        return HttpResponseForbidden("El proyecto esta vencido y no puedes crear tareas.")
    
    if request.method == 'POST':
        form = TaskForm(request.POST, workspace=project.workspace)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            # Si el status viene del formulario, lo usamos. Si no, default.
            if not task.status:
                task.status = Task.Status.BACKLOG
            task.save()
            
            # Logica de actividad
            verb_text = f'creó la tarea "{task.title}"'
            Activity.objects.create(project=project, actor=request.user, verb=verb_text, target=task)
            # Fin logica actividad
            
            # Logica de notificacion
            if task.assignee is not None:
                # Nos aseguramos de no notificar al autor de la tarea
                if task.assignee != request.user:
                    Notification.objects.create(
                        recipient=task.assignee,
                        actor=request.user,
                        verb='te asignó la tarea',
                        target=task
                    )
            # Fin de la logica de notificacion
            
            # Devolvemos la tarjeta de la nueva tarea para que htmx la inserte
            return render(request, 'core/_task_card.html', {'task': task})
    
    # Si la petición es GET, devolvemos el formulario vacío para el modal
    form = TaskForm(workspace=project.workspace, initial={'status': 'BACKLOG'})
    return render(request, 'core/_task_form.html', {'form': form, 'project': project})


@login_required
def task_detail_update(request, pk):
    # Buscamos la tarea y verificamos los permisos del usuario
    task = get_object_or_404(Task, pk=pk, project__workspace__members=request.user)
    
    # Guardamos el asignado original ANTES de procesar el formulario
    old_assignee = task.assignee
    
    if request.method == 'POST':
        if not can_user_interact_with_project(task.project, request.user):
            return HttpResponseForbidden("El proyecto esta vencido y no puedes editar la tarea.")
        
        form = TaskForm(request.POST, instance=task, workspace=task.project.workspace)
        if form.is_valid():
            update_task = form.save()
            
            # Logica de actividad
            verb_text = f'actualizó la tarea "{update_task.title}"'
            Activity.objects.create(project=task.project, actor=request.user, verb=verb_text, target=update_task)
            # Fin logica actividad
            
            # Logica de notificacion de asignacion
            new_assignee = update_task.assignee
            if new_assignee != old_assignee and new_assignee is not None:
                # nos aseguramos de no notificar al autor del cambio
                Notification.objects.create(
                    recipient=new_assignee,
                    actor=request.user,
                    verb='te asignó la tarea',
                    target=update_task
                )
            # Fin de la logica de notificacion
            
            # Devolvemos la tarjeta actualizada para que htmx la reemplace en el tablero
            return render(request, 'core/_task_card.html', {'task': update_task})
    else:
        # si la peticion es GET, mostramos el formulario con los datos de la tarea
        form = TaskForm(instance=task, workspace=task.project.workspace)
        
    context = {
        'form': form,
        'task': task,
        'comment_form': CommentForm()
    }
    
    # Devolvemos el formulario dentro de la estructura del modal.
    return render(request, 'core/_task_detail_modal.html', context)


@login_required
@require_POST
def add_comment(request, task_pk):
    task = get_object_or_404(Task, pk=task_pk, project__workspace__members=request.user)
    
    # Verificamos si el usuario puede interactuar
    if not can_user_interact_with_project(task.project, request.user):
        return HttpResponseForbidden("El proyecto está vencido y no puedes comentar.")

    form = CommentForm(request.POST, request.FILES)

    if form.is_valid():
        # Primero, creamos el objeto Comment
        comment = Comment.objects.create(
            task=task,
            author=request.user,
            text=form.cleaned_data['text']
        )
        
        # Logica de actividad
        verb_text = 'comentó en la tarea'
        Activity.objects.create(project=task.project, actor=request.user, verb=verb_text, target=task)
        # Fin logica actividad
        
        # Logica notificacion
        # Creamos un conjunto de usuarios a notificar para evitar duplicados
        recipients = set()
        # Añadimos a la persona a la tarea si existe
        if task.assignee:
            recipients.add(task.assignee)
        # Añadimos al dueño del workspace
        recipients.add(task.project.workspace.owner)
        # Nos aseguramos de no hacer la notificacion al autor del comentario
        recipients.discard(request.user)
        # Creamos una notificación para cada usuario en el conjunto
        for user in recipients:
            Notification.objects.create(
                recipient=user,
                actor=request.user,
                verb='comentó en la tarea',
                target=task
            )

        # Si el usuario subió un archivo, creamos el objeto Attachment
        uploaded_file = form.cleaned_data.get('file')
        if uploaded_file:
            Attachment.objects.create(
                comment=comment,
                uploader=request.user,
                file=uploaded_file
            )
        
        # Devolvemos el HTML del nuevo comentario para que htmx lo añada
        return render(request, 'core/_comment_item.html', {'comment': comment})
    
    return HttpResponse("Error en el formulario.", status=400)



class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'core/notification_list.html'
    content_type_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        # Marcar las no leidas como leidas al cargar la pagina
        unread_notifications = self.request.user.notifications.filter(read=False)
        unread_notifications.update(read=True)
        # Devolver todas las notificaciones
        return self.request.user.notifications.all()
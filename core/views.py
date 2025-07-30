from datetime import timedelta
from django.shortcuts import render
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Workspace, Membership, Project, Task, Comment, Attachment, Notification, Activity, Invitation, TimeLog, Role, CustomField ,CustomFieldValue
from .forms import WorkspaceForm, ProjectForm, TaskForm, CommentForm, InvitationForm, RoleForm, CustomFieldForm
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .utils import can_user_interact_with_project
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
from collections import defaultdict

User = get_user_model()

class LandingPageView(TemplateView):
    template_name = 'core/landing_page.html'

class WorkspaceListView(LoginRequiredMixin, ListView):
    model = Workspace
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # --- 1. LÓGICA PARA LISTAR WORKSPACES  ---
        # Esto es necesario para TODOS los roles.
        context['owned_workspaces'] = Workspace.objects.filter(owner=user)
        context['shared_workspaces'] = user.workspaces.exclude(owner=user)
        context['my_tasks'] = Task.objects.filter(assignee=user).exclude(status=Task.Status.DONE).order_by('due_date')

        # --- 2. LÓGICA PARA WIDGETS POR ROL ---
        # Verificamos si el usuario tiene el rol de PMO
        is_pmo = user.memberships.filter(role__name='PMO').exists()
        context['is_pmo'] = is_pmo

        if is_pmo:
            # Obtenemos todos los proyectos de los workspaces que el usuario posee
            # Nota: Podríamos cambiar esta lógica para incluir workspaces donde es PMO pero no dueño
            workspaces = Workspace.objects.filter(owner=user)
            all_projects = Project.objects.filter(workspace__in=workspaces)
            
            # Buscamos tareas en riesgo
            today = timezone.now().date()
            next_week = today + timedelta(days=7)
            context['at_risk_tasks'] = Task.objects.filter(
                project__in=all_projects,
                due_date__gte=today,
                due_date__lte=next_week
            ).exclude(status=Task.Status.DONE)
            
            # Buscamos tareas ya vencidas
            context['overdue_tasks'] = Task.objects.filter(
                project__in=all_projects,
                due_date__lt=today
            ).exclude(status=Task.Status.DONE)

        else:
            # Mostramos las tareas asignadas al usuario actual
            context['my_tasks'] = Task.objects.filter(assignee=user).exclude(status=Task.Status.DONE).order_by('due_date')

        return context

class WorkspaceCreateView(LoginRequiredMixin, CreateView):
    model = Workspace
    form_class = WorkspaceForm
    template_name = 'core/workspace_form.html'
    success_url = reverse_lazy('core:workspace_list')
    
    def form_valid(self, form):
        # Asigna el owner del workspace al usuario actual
        form.instance.owner = self.request.user
        # llama al método form_valid del padre para guardar el workspace
        response = super().form_valid(form)
        # 3. Obtenemos el rol 'Dueño' (o lo creamos si no existe)
        owner_role = Role.objects.get_or_create(name='Dueño')
        # Crea la membresia para el owner, asignandole el rol de 'ADMIN'
        Membership.objects.create(
            user=self.request.user, 
            workspace=self.object,  # Es el workspace recién creado
            role=owner_role)
        
        return response
    

class WorkspaceDetailView(LoginRequiredMixin, DetailView):
    model = Workspace
    slug_url_kwarg = 'workspace_slug'
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
    
    
@login_required
def project_create_form(request, workspace_slug):
    workspace = get_object_or_404(Workspace, slug=workspace_slug, owner=request.user)
    form = ProjectForm()
    return render(request, 'core/_project_create_modal.html', {'form': form, 'workspace': workspace})


@login_required
@require_POST
def project_create_action(request, workspace_slug):
    workspace = get_object_or_404(Workspace, slug=workspace_slug, owner=request.user)
    form = ProjectForm(request.POST)

    if form.is_valid():
        project = form.save(commit=False)
        project.workspace = workspace
        project.save()
        # Devolvemos la plantilla de la tarjeta con el proyecto recién creado
        return render(request, 'core/_project_card.html', {'project': project})
    
    # Si el formulario no es válido, devuelve un error
    return HttpResponse("Error en el formulario", status=400)    

    
class WorkspaceManageView(LoginRequiredMixin, DetailView):
    model = Workspace
    slug_url_kwarg = 'workspace_slug'
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
        context['all_roles'] = Role.objects.all()
        context['role_form'] = RoleForm()
        context['custom_field_form'] = CustomFieldForm()
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
    # El error estaba en esta línea. Cambiamos 'accepted' por 'is_accepted'.
    invitation = get_object_or_404(Invitation, token=token, is_accepted=False)
    
    workspace = invitation.workspace
    user = request.user

    # Verificamos si el usuario ya es miembro para no añadirlo dos veces
    if workspace.members.filter(id=user.id).exists():
        messages.warning(request, "Ya eres miembro de este equipo.")
        return redirect('core:workspace_detail', slug=workspace.slug)

    # Si todo está en orden, añadimos al usuario al equipo
    Membership.objects.create(
        user=user,
        workspace=workspace,
        role=Membership.Role.MEMBER
    )

    # Marcamos la invitación como utilizada
    invitation.is_accepted = True
    invitation.save()

    # Creamos un registro de actividad y notificaciones
    verb_text = f'se unió al equipo "{workspace.name}"'
    # Corregimos el target para que apunte al workspace, no a un proyecto nulo
    Activity.objects.create(project=None, actor=user, verb=verb_text, target=workspace)
    
    # Notificamos al dueño del workspace
    Notification.objects.create(
        recipient=workspace.owner,
        actor=user,
        verb='aceptó tu invitación para unirse al equipo',
        target=workspace
    )

    messages.success(request, f"¡Bienvenido! Has sido añadido al equipo '{workspace.name}'.")
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
    slug_url_kwarg = 'project_slug'
    template_name = 'core/project_detail.html'
    context_object_name = 'project'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        
        #----- Logica de busqueda ------
        tasks = project.tasks.all()
        search_query = self.request.GET.get('q', '')
        
        if search_query:
            tasks = tasks.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        # ----- Fin de la Logica de busqueda ------
        
        #--- Logica de Filtrado ----
        # Obtenemos el parametro del filtro desde la URL
        filter_by = self.request.GET.get('filter_by')
        # Si el filtro es 'my_tasks', filtramos el queryset
        if filter_by == 'my_tasks':
            tasks = tasks.filter(assignee=self.request.user)
        context['active_filter'] = filter_by
        context['search_query'] = search_query
        #----- Fin de la Logica de Filtrado -----
        
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
        context['activities'] = self.get_object().activities.all()[:5] # Mostramos las 15 más recientes
        
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
        
        # --- INICIO DE LA LÓGICA DE DEPENDENCIA ---
        # Solo verificamos si se intenta mover a "En Progreso"
        if new_status_key == Task.Status.IN_PROGRESS:
            # Buscamos si hay alguna tarea predecesora que NO esté completada
            incomplete_predecessors = task.predecessors.exclude(status=Task.Status.DONE)
            if incomplete_predecessors.exists():
                # Si existen, devolvemos un error y no hacemos el cambio
                return HttpResponse("No se puede iniciar esta tarea. Una o más de sus predecesoras no están completadas.", status=400) # 400 Bad Request
        # --- FIN DE LA LÓGICA DE DEPENDENCIA ---
        
        # Guardamos el estado anterior para la notificacion
        old_status_label = task.get_status_display()
        
        task.status = new_status_key
        task.save(update_fields=['status']) # Actualiza solo el campo 'status'
        
        # ---- Logica AUTOMATIZACION ------
        if new_status_key == Task.Status.DONE:
            try:
                # Intenta obtener el usuario bot que creamos
                bot_find = 'nexus-bot'
                bot_user = User.objects.get(username=bot_find)
                Comment.objects.create(
                    task=task,
                    author=bot_user,
                    text='¡Tarea Finalizada! Pendiente de revisión.'
                )
                
            except User.DoesNotExist:
                # Si el bot no existe, no hacemos nada para no causar un error
                print("Advertencia: El usuario 'nexus-bot' no existe para la Automatización.")
        # ---- Fin de la Logica AUTOMATIZACION ------
        
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
        form = TaskForm(request.POST, project=project)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            if not task.status:
                task.status = Task.Status.BACKLOG
            task.save()
            
            # Logica de actividad
            verb_text = f'creó la tarea "{task.title}"'
            Activity.objects.create(project=project, actor=request.user, verb=verb_text, target=task)
            
            # Logica de notificacion
            if task.assignee is not None:
                if task.assignee != request.user:
                    Notification.objects.create(
                        recipient=task.assignee,
                        actor=request.user,
                        verb='te asignó la tarea',
                        target=task
                    )
                    
            return render(request, 'core/_task_card.html', {'task': task})
        
        # Si el form no es válido, se renderiza el formulario con errores
        return render(request, 'core/_task_form.html', {'form': form, 'project': project})

    else: # Peticion GET
        form = TaskForm(project=project, initial={'status': 'BACKLOG'})
        return render(request, 'core/_task_form.html', {'form': form, 'project': project})


@login_required
def task_detail_update(request, pk):
    # 1. Obtenemos los objetos principales al principio
    task = get_object_or_404(Task, pk=pk, project__workspace__members=request.user)
    can_edit = (request.user == task.project.workspace.owner or request.user == task.assignee)
    active_log = TimeLog.objects.filter(task=task, user=request.user, end_time__isnull=True).first()
    is_timer_active = active_log is not None

    # 2. Manejamos la lógica del formulario POST
    if request.method == 'POST':
        if not can_user_interact_with_project(task.project, request.user) or not can_edit:
            return HttpResponseForbidden("No tienes permiso para editar esta tarea.")
            
        form = TaskForm(request.POST, instance=task, project=task.project)
        if form.is_valid():
            updated_task = form.save()
            # --- INICIO DE LA LÓGICA PARA GUARDAR CAMPOS PERSONALIZADOS ---
            custom_fields = updated_task.project.workspace.custom_fields.all()
            for field in custom_fields:
                field_name = f'custom_field_{field.id}'
                value = request.POST.get(field_name)

                if value:
                    # Buscamos si ya existe un valor para este campo y tarea
                    value_obj, created = CustomFieldValue.objects.get_or_create(
                        task=updated_task,
                        field=field
                    )
                    
                    # Guardamos el valor en la columna correcta según el tipo
                    if field.field_type == CustomField.FieldType.TEXT:
                        value_obj.value_text = value
                    elif field.field_type == CustomField.FieldType.NUMBER:
                        value_obj.value_number = value
                    elif field.field_type == CustomField.FieldType.DATE:
                        value_obj.value_date = value
                    elif field.field_type == CustomField.FieldType.DROPDOWN:
                        value_obj.value_option_id = value
                    
                    value_obj.save()
            # --- FIN DE LA LÓGICA ---
            return render(request, 'core/_task_update_success.html', {'task': updated_task})
        # Si el formulario NO es válido, la función continúa y renderiza el modal con los errores al final
    else: # Petición GET
        form = TaskForm(instance=task, project=task.project)
        if not can_edit:
            for field in form.fields.values():
                field.widget.attrs['disabled'] = True
    
    # 3. El contexto se crea aquí, asegurando que SIEMPRE tenga todas las variables
    context = {
        'form': form,
        'task': task,
        'comment_form': CommentForm(),
        'can_edit': can_edit,
        'is_timer_active': is_timer_active,
        'active_log': active_log,
    }
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
    context_object_name = 'notifications'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        """
        Este método se ejecuta ANTES que get_queryset.
        Es el lugar perfecto para realizar la acción de marcar como leído.
        """
        # Actualizamos todas las notificaciones no leídas del usuario a 'leído'.
        request.user.notifications.filter(read=False).update(read=True)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """
        Ahora este método solo tiene una responsabilidad: obtener la lista.
        """
        return self.request.user.notifications.all()
    
    

class ProjectGanttView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'core/project_gantt.html'
    context_object_name = 'project'
    slug_url_kwarg = 'project_slug'

    def get_queryset(self):
        return Project.objects.filter(workspace__members=self.request.user)
    

def project_gantt_data(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug, workspace__members=request.user)
    tasks = project.tasks.filter(
        start_date__isnull=False, 
        due_date__isnull=False
    ).order_by('start_date')

    gantt_tasks = []
    for task in tasks:
        # --- INICIO DE LA CORRECCIÓN CLAVE ---
        # Unimos los IDs de las predecesoras en un solo string separado por comas
        dependencies_str = ",".join([f'task_{p.id}' for p in task.predecessors.all()])
        # --- FIN DE LA CORRECCIÓN CLAVE ---

        progress = 100 if task.status == Task.Status.DONE else 0
        custom_class = f'bar-{task.status.lower()}'
        assigne_name = task.assignee.get_full_name() if task.assignee else 'Sin Asignar'
        gantt_tasks.append({
            'id': f'task_{task.id}',
            'name': task.title,
            'start': task.start_date.strftime('%Y-%m-%d'),
            'end': task.due_date.strftime('%Y-%m-%d'),
            'progress': progress,
            'dependencies': dependencies_str,  # Pasamos el string, no la lista
            'custom_class': custom_class,
            'assignee': assigne_name,
        })

    return JsonResponse(gantt_tasks, safe=False)


@login_required
@require_POST
def toggle_time_log(request, task_pk):
    task = get_object_or_404(Task, pk=task_pk, project__workspace__members=request.user)
    
    active_log = TimeLog.objects.filter(
        task=task, user=request.user, end_time__isnull=True
    ).first()

    if active_log:
        # Si hay un log activo, lo detenemos
        active_log.end_time = timezone.now()
        active_log.save()
        return JsonResponse({
            'status': 'stopped',
            'total_logged_time': task.formatted_total_logged_time
        })
    else:
        # Si no hay log activo, creamos uno nuevo
        new_log = TimeLog.objects.create(task=task, user=request.user)
        return JsonResponse({
            'status': 'started',
            'start_time': new_log.start_time.isoformat() # Enviamos la hora de inicio exacta
        })


class TeamDirectoryView(LoginRequiredMixin, DetailView):
    model = Workspace
    template_name = 'core/team_directory.html'
    context_object_name = 'workspace'
    slug_url_kwarg = 'workspace_slug'

    def dispatch(self, request, *args, **kwargs):
        workspace = self.get_object()
        try:
            membership = request.user.memberships.get(workspace=workspace)
            # CAMBIAMOS LA LÓGICA: ahora revisa el campo booleano
            if not membership.role.is_admin_role:
                messages.error(request, "No tienes permiso para ver el directorio del equipo.")
                return redirect('core:workspace_detail', workspace_slug=workspace.slug)
        except (Membership.DoesNotExist, AttributeError):
            # Capturamos también AttributeError por si el rol es Nulo
            messages.error(request, "No eres miembro o no tienes un rol asignado en este equipo.")
            return redirect('core:workspace_list')
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace = self.get_object()
        
        # Agrupamos los miembros por rol
        members_by_role = defaultdict(list)
        for membership in workspace.membership_set.all().order_by('role__name'):
            members_by_role[membership.role.name].append(membership.user)
        
        context['grouped_members'] = dict(members_by_role)
        return context
    
    
class ProjectReportsView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'core/project_reports.html'
    context_object_name = 'project'
    slug_url_kwarg = 'project_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        
        # Logica para los widgets de puntos criticos
        today = timezone.now().date()
        
        # Tareas vencidas 
        context['overdue_tasks'] = project.tasks.filter(
            due_date__lt=today
        ).exclude(status=Task.Status.DONE)
        
        # Tareas en riesgo (Vencen en los procimos 7 dias)
        next_week = today + timedelta(days=7)
        context['at_risk_tasks'] = project.tasks.filter(
            due_date__gte=today,
            due_date__lte=next_week
        ).exclude(status=Task.Status.DONE)
        
        # Reporte de carga de trabajo
        workload = project.tasks.exclude(
            status__in=[Task.Status.DONE, Task.Status.CANCELED]
        ).filter(
            assignee__isnull=False
        ).values(
            'assignee__first_name', 'assignee__last_name' # Obtenemos nombre y apellido
        ).annotate(
            total_points=Sum('effort_points')
        ).order_by('-total_points')
        
        context['workload_data'] = workload
        
        # Preparamos los datos para el gráfico
        workload_labels = [f"{w['assignee__first_name']} {w['assignee__last_name']}" for w in workload]
        workload_values = [w['total_points'] for w in workload]
        
        context['workload_labels'] = workload_labels
        context['workload_values'] = workload_values
        
        return context
    
    
@login_required
@require_POST
def update_member_role(request, membership_id):
    # Buscamos la membresía específica
    membership = get_object_or_404(Membership, id=membership_id)
    workspace = membership.workspace

    # Verificación de seguridad: solo el dueño del workspace puede cambiar roles
    if workspace.owner != request.user:
        return HttpResponseForbidden("No tienes permiso para cambiar roles en este equipo.")

    new_role_id = request.POST.get('role')
    if new_role_id:
        new_role = get_object_or_404(Role, id=new_role_id)
        membership.role = new_role
        membership.save()
        messages.success(request, f"Se actualizó el rol de {membership.user.get_full_name()}.")
    
    return redirect('core:workspace_manage', workspace_slug=workspace.slug)


@login_required
@require_POST
def create_role(request, workspace_slug):
    workspace = get_object_or_404(Workspace, slug=workspace_slug, owner=request.user)
    form = RoleForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, f"Se ha creado el nuevo rol '{form.cleaned_data['name']}'.")
    else:
        # Si hay errores (ej: el rol ya existe), los mostramos
        for error in form.errors.values():
            messages.error(request, error)
            
    return redirect('core:workspace_manage', workspace_slug=workspace.slug)


@login_required
@require_POST
def create_custom_field(request, workspace_slug):
    workspace = get_object_or_404(Workspace, slug=workspace_slug, owner=request.user)
    form = CustomFieldForm(request.POST)
    if form.is_valid():
        field = form.save(commit=False)
        field.workspace = workspace
        field.save()
        messages.success(request, f'Se ha creado el campo personalizado "{field.name}".')
    else:
        messages.error(request, 'Error al crear el campo.')
    return redirect('core:workspace_manage', workspace_slug=workspace.slug)
# Script CORREGIDO para Crear Datos de Prueba - Nexus PM
# Reemplaza el contenido de: core/management/commands/create_test_data.py

import os
import django
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import IntegrityError

# Importar todos los modelos
from core.models import (
    Workspace, Project, Task, Role, Membership, 
    Comment, Activity, CustomField, FieldOption, CustomFieldValue
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Crea datos de prueba para el proyecto Nexus PM'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Iniciando creación de datos de prueba...'))
        
        # 1. Crear usuarios de prueba
        self.create_users()
        
        # 2. Crear roles
        self.create_roles()
        
        # 3. Crear workspaces
        self.create_workspaces()
        
        # 4. Crear proyectos
        self.create_projects()
        
        # 5. Crear tareas
        self.create_tasks()
        
        # 6. Crear campos personalizados
        self.create_custom_fields()
        
        # 7. Crear comentarios
        self.create_comments()
        
        self.stdout.write(self.style.SUCCESS('✅ ¡Datos de prueba creados exitosamente!'))
        self.print_summary()

    def create_users(self):
        """Crear usuarios de prueba"""
        self.stdout.write('👥 Creando usuarios de prueba...')
        
        # Usuario administrador principal - usar el existente o crear uno nuevo
        admin_candidates = [
            ('admin@nexuspm.com', 'admin_nexus'),
            ('admin@example.com', 'admin_ejemplo'),
            ('superuser@nexuspm.com', 'superuser')
        ]
        
        self.admin_user = None
        
        # Primero intentar encontrar un superusuario existente
        existing_superuser = User.objects.filter(is_superuser=True).first()
        if existing_superuser:
            self.admin_user = existing_superuser
            self.stdout.write(f'   ✓ Usando superusuario existente: {existing_superuser.email}')
        else:
            # Si no hay superusuario, crear uno
            for email, username in admin_candidates:
                try:
                    self.admin_user = User.objects.create_superuser(
                        username=username,
                        email=email,
                        password='admin123',
                        first_name='Admin',
                        last_name='Principal'
                    )
                    self.stdout.write(f'   ✓ Superusuario creado: {email} / admin123')
                    break
                except IntegrityError:
                    continue
        
        if not self.admin_user:
            self.stdout.write(self.style.ERROR('   ❌ No se pudo crear/encontrar superusuario'))
            return

        # PMO (Project Management Office)
        self.pmo_user = self.get_or_create_user(
            email='pmo@nexuspm.com',
            username='pmo_manager',
            first_name='María',
            last_name='González',
            password='pmo123',
            is_staff=True
        )

        # Desarrollador Senior
        self.dev_senior = self.get_or_create_user(
            email='dev.senior@nexuspm.com',
            username='dev_senior',
            first_name='Carlos',
            last_name='Rodríguez',
            password='dev123'
        )

        # Desarrollador Junior
        self.dev_junior = self.get_or_create_user(
            email='dev.junior@nexuspm.com',
            username='dev_junior',
            first_name='Ana',
            last_name='López',
            password='dev123'
        )

        # Diseñador UX/UI
        self.designer = self.get_or_create_user(
            email='designer@nexuspm.com',
            username='ux_designer',
            first_name='Sofia',
            last_name='Martinez',
            password='design123'
        )

    def get_or_create_user(self, email, username, first_name, last_name, password, is_staff=False):
        """Método auxiliar para crear usuarios con manejo de duplicados"""
        
        # Primero buscar por email
        user = User.objects.filter(email=email).first()
        if user:
            self.stdout.write(f'   ✓ Usuario ya existe: {email}')
            return user
            
        # Si no existe, intentar crear con diferentes usernames si es necesario
        username_attempts = [username, f"{username}1", f"{username}_2025", f"{username}_{first_name.lower()}"]
        
        for attempt_username in username_attempts:
            try:
                user = User.objects.create_user(
                    username=attempt_username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=is_staff
                )
                self.stdout.write(f'   ✓ Usuario creado: {email} / {password}')
                return user
            except IntegrityError:
                continue
                
        # Si llegamos aquí, no se pudo crear
        self.stdout.write(self.style.WARNING(f'   ⚠️ No se pudo crear usuario: {email}'))
        return None

    def create_roles(self):
        """Crear roles del sistema"""
        self.stdout.write('🎭 Creando roles del sistema...')
        
        roles_data = [
            ('Dueño', 'Propietario del workspace con todos los permisos', True),
            ('PMO', 'Project Management Office - Gestión de proyectos', True),
            ('Desarrollador Senior', 'Desarrollador con experiencia y liderazgo técnico', False),
            ('Desarrollador Junior', 'Desarrollador en formación', False),
            ('Diseñador UX/UI', 'Especialista en experiencia y diseño de usuario', False),
            ('Tester/QA', 'Especialista en pruebas y calidad', False),
            ('Cliente', 'Cliente externo con acceso limitado', False),
        ]
        
        for name, description, is_admin in roles_data:
            role, created = Role.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'is_admin_role': is_admin
                }
            )
            if created:
                self.stdout.write(f'   ✓ Rol creado: {name}')

    def create_workspaces(self):
        """Crear workspaces de prueba"""
        self.stdout.write('🏢 Creando workspaces de prueba...')
        
        # Workspace principal
        self.main_workspace, created = Workspace.objects.get_or_create(
            name='Desarrollo de Software',
            defaults={
                'owner': self.admin_user,
            }
        )
        if created:
            self.stdout.write(f'   ✓ Workspace creado: {self.main_workspace.name}')

        # Añadir miembros al workspace
        members_data = [
            (self.admin_user, 'Dueño'),
            (self.pmo_user, 'PMO'),
            (self.dev_senior, 'Desarrollador Senior'),
            (self.dev_junior, 'Desarrollador Junior'),
            (self.designer, 'Diseñador UX/UI'),
        ]
        
        for user, role_name in members_data:
            if user:  # Solo si el usuario existe
                role = Role.objects.get(name=role_name)
                membership, created = Membership.objects.get_or_create(
                    user=user,
                    workspace=self.main_workspace,
                    defaults={'role': role}
                )
                if created:
                    self.stdout.write(f'   ✓ Miembro añadido: {user.get_full_name()} como {role_name}')

        # Workspace secundario (solo si existe el PMO user)
        if self.pmo_user:
            self.secondary_workspace, created = Workspace.objects.get_or_create(
                name='Marketing Digital',
                defaults={
                    'owner': self.pmo_user,
                }
            )
            if created:
                # Añadir algunos miembros
                Membership.objects.get_or_create(
                    user=self.pmo_user,
                    workspace=self.secondary_workspace,
                    defaults={'role': Role.objects.get(name='Dueño')}
                )
                if self.designer:
                    Membership.objects.get_or_create(
                        user=self.designer,
                        workspace=self.secondary_workspace,
                        defaults={'role': Role.objects.get(name='Diseñador UX/UI')}
                    )
                self.stdout.write(f'   ✓ Workspace creado: {self.secondary_workspace.name}')
        else:
            self.secondary_workspace = None

    def create_projects(self):
        """Crear proyectos de prueba"""
        self.stdout.write('📁 Creando proyectos de prueba...')
        
        # Proyecto 1: Sistema de Gestión
        self.project1, created = Project.objects.get_or_create(
            name='Sistema de Gestión de Inventario',
            defaults={
                'workspace': self.main_workspace,
                'description': 'Desarrollo de un sistema completo para gestión de inventario con dashboard en tiempo real, reportería avanzada y integración con APIs externas.',
                'status': Project.Status.ACTIVE,
                'manager': self.dev_senior if self.dev_senior else self.admin_user,
                'budget': 50000.00,
                'deadline': timezone.now().date() + timedelta(days=60)
            }
        )
        if created:
            self.stdout.write(f'   ✓ Proyecto creado: {self.project1.name}')

        # Proyecto 2: App Mobile
        self.project2, created = Project.objects.get_or_create(
            name='App Mobile para Delivery',
            defaults={
                'workspace': self.main_workspace,
                'description': 'Aplicación móvil nativa para iOS y Android, incluyendo sistema de pedidos, tracking GPS y pasarelas de pago.',
                'status': Project.Status.ACTIVE,
                'manager': self.pmo_user if self.pmo_user else self.admin_user,
                'budget': 75000.00,
                'deadline': timezone.now().date() + timedelta(days=90)
            }
        )
        if created:
            self.stdout.write(f'   ✓ Proyecto creado: {self.project2.name}')

        # Proyecto 3: Campaña de Marketing (solo si existe workspace secundario)
        if self.secondary_workspace:
            self.project3, created = Project.objects.get_or_create(
                name='Campaña Q4 2025',
                defaults={
                    'workspace': self.secondary_workspace,
                    'description': 'Campaña de marketing digital para el último trimestre, incluyendo redes sociales, Google Ads y email marketing.',
                    'status': Project.Status.ACTIVE,
                    'manager': self.designer if self.designer else self.pmo_user,
                    'budget': 25000.00,
                    'deadline': timezone.now().date() + timedelta(days=30)
                }
            )
            if created:
                self.stdout.write(f'   ✓ Proyecto creado: {self.project3.name}')
        else:
            self.project3 = None

    def create_tasks(self):
        """Crear tareas de prueba"""
        self.stdout.write('📝 Creando tareas de prueba...')
        
        # Tareas para Proyecto 1 - Sistema de Inventario
        tasks_proyecto1 = [
            {
                'title': 'Análisis de Requerimientos',
                'description': 'Reunir y documentar todos los requerimientos funcionales y no funcionales del sistema.',
                'status': Task.Status.DONE,
                'priority': Task.Priority.HIGH,
                'assignee': self.pmo_user if self.pmo_user else self.admin_user,
                'effort_points': 8,
                'start_date': timezone.now().date() - timedelta(days=20),
                'due_date': timezone.now().date() - timedelta(days=15),
            },
            {
                'title': 'Diseño de Base de Datos',
                'description': 'Crear el modelo entidad-relación y esquema de base de datos optimizado.',
                'status': Task.Status.DONE,
                'priority': Task.Priority.HIGH,
                'assignee': self.dev_senior if self.dev_senior else self.admin_user,
                'effort_points': 5,
                'start_date': timezone.now().date() - timedelta(days=15),
                'due_date': timezone.now().date() - timedelta(days=10),
            },
            {
                'title': 'Desarrollo API REST',
                'description': 'Implementar endpoints para CRUD de productos, categorías y movimientos de inventario.',
                'status': Task.Status.IN_PROGRESS,
                'priority': Task.Priority.HIGH,
                'assignee': self.dev_senior if self.dev_senior else self.admin_user,
                'effort_points': 13,
                'start_date': timezone.now().date() - timedelta(days=10),
                'due_date': timezone.now().date() + timedelta(days=15),
            },
            {
                'title': 'Dashboard Frontend',
                'description': 'Crear dashboard interactivo con gráficos en tiempo real y métricas clave.',
                'status': Task.Status.TODO,
                'priority': Task.Priority.MEDIUM,
                'assignee': self.dev_junior if self.dev_junior else self.admin_user,
                'effort_points': 8,
                'start_date': timezone.now().date() + timedelta(days=5),
                'due_date': timezone.now().date() + timedelta(days=25),
            },
            {
                'title': 'Sistema de Notificaciones',
                'description': 'Implementar notificaciones push y por email para alertas de stock bajo.',
                'status': Task.Status.BACKLOG,
                'priority': Task.Priority.LOW,
                'assignee': self.dev_junior if self.dev_junior else self.admin_user,
                'effort_points': 5,
                'start_date': timezone.now().date() + timedelta(days=20),
                'due_date': timezone.now().date() + timedelta(days=35),
            },
        ]

        # Crear tareas del proyecto 1
        created_tasks = []
        for task_data in tasks_proyecto1:
            task, created = Task.objects.get_or_create(
                title=task_data['title'],
                project=self.project1,
                defaults=task_data
            )
            if created:
                created_tasks.append(task)
                self.stdout.write(f'   ✓ Tarea creada: {task.title}')

        # Establecer dependencias (solo si se crearon las tareas)
        try:
            api_task = Task.objects.get(title='Desarrollo API REST', project=self.project1)
            db_task = Task.objects.get(title='Diseño de Base de Datos', project=self.project1)
            api_task.predecessors.add(db_task)
            
            dashboard_task = Task.objects.get(title='Dashboard Frontend', project=self.project1)
            dashboard_task.predecessors.add(api_task)
            self.stdout.write(f'   ✓ Dependencias establecidas entre tareas')
        except Task.DoesNotExist:
            pass

        # Tareas para Proyecto 2 - App Mobile
        tasks_proyecto2 = [
            {
                'title': 'Wireframes y Mockups',
                'description': 'Diseñar wireframes de baja y alta fidelidad para todas las pantallas de la app.',
                'status': Task.Status.DONE,
                'priority': Task.Priority.HIGH,
                'assignee': self.designer if self.designer else self.admin_user,
                'effort_points': 8,
                'start_date': timezone.now().date() - timedelta(days=25),
                'due_date': timezone.now().date() - timedelta(days=18),
            },
            {
                'title': 'Setup Proyecto React Native',
                'description': 'Configurar proyecto React Native con navegación, estado global y arquitectura base.',
                'status': Task.Status.IN_PROGRESS,
                'priority': Task.Priority.HIGH,
                'assignee': self.dev_senior if self.dev_senior else self.admin_user,
                'effort_points': 5,
                'start_date': timezone.now().date() - timedelta(days=7),
                'due_date': timezone.now().date() + timedelta(days=5),
            },
            {
                'title': 'Integración Pasarelas de Pago',
                'description': 'Integrar Stripe y PayPal para procesamiento de pagos seguros.',
                'status': Task.Status.TODO,
                'priority': Task.Priority.CRITICAL,
                'assignee': self.dev_senior if self.dev_senior else self.admin_user,
                'effort_points': 13,
                'start_date': timezone.now().date() + timedelta(days=10),
                'due_date': timezone.now().date() + timedelta(days=30),
            },
        ]

        for task_data in tasks_proyecto2:
            task, created = Task.objects.get_or_create(
                title=task_data['title'],
                project=self.project2,
                defaults=task_data
            )
            if created:
                self.stdout.write(f'   ✓ Tarea creada: {task.title}')

        # Tareas para Proyecto 3 - Marketing (solo si existe)
        if self.project3:
            tasks_proyecto3 = [
                {
                    'title': 'Estrategia de Contenido',
                    'description': 'Definir calendario editorial y tipos de contenido para redes sociales.',
                    'status': Task.Status.IN_PROGRESS,
                    'priority': Task.Priority.HIGH,
                    'assignee': self.designer if self.designer else self.admin_user,
                    'effort_points': 3,
                    'start_date': timezone.now().date() - timedelta(days=5),
                    'due_date': timezone.now().date() + timedelta(days=10),
                },
                {
                    'title': 'Diseño de Creatividades',
                    'description': 'Crear banners, stories y posts para Facebook, Instagram y LinkedIn.',
                    'status': Task.Status.TODO,
                    'priority': Task.Priority.MEDIUM,
                    'assignee': self.designer if self.designer else self.admin_user,
                    'effort_points': 8,
                    'start_date': timezone.now().date() + timedelta(days=8),
                    'due_date': timezone.now().date() + timedelta(days=20),
                },
            ]

            for task_data in tasks_proyecto3:
                task, created = Task.objects.get_or_create(
                    title=task_data['title'],
                    project=self.project3,
                    defaults=task_data
                )
                if created:
                    self.stdout.write(f'   ✓ Tarea creada: {task.title}')

    def create_custom_fields(self):
        """Crear campos personalizados de ejemplo"""
        self.stdout.write('🔧 Creando campos personalizados...')
        
        # Campo de prioridad de negocio
        priority_field, created = CustomField.objects.get_or_create(
            workspace=self.main_workspace,
            name='Prioridad de Negocio',
            defaults={'field_type': CustomField.FieldType.DROPDOWN}
        )
        if created:
            # Crear opciones para el dropdown
            options = ['Muy Alta', 'Alta', 'Media', 'Baja']
            for option_value in options:
                FieldOption.objects.get_or_create(
                    custom_field=priority_field,
                    value=option_value
                )
            self.stdout.write(f'   ✓ Campo personalizado creado: {priority_field.name}')

        # Campo de estimación en horas
        hours_field, created = CustomField.objects.get_or_create(
            workspace=self.main_workspace,
            name='Estimación (Horas)',
            defaults={'field_type': CustomField.FieldType.NUMBER}
        )
        if created:
            self.stdout.write(f'   ✓ Campo personalizado creado: {hours_field.name}')

        # Campo de fecha de revisión
        review_field, created = CustomField.objects.get_or_create(
            workspace=self.main_workspace,
            name='Fecha de Revisión',
            defaults={'field_type': CustomField.FieldType.DATE}
        )
        if created:
            self.stdout.write(f'   ✓ Campo personalizado creado: {review_field.name}')

    def create_comments(self):
        """Crear comentarios de ejemplo"""
        self.stdout.write('💬 Creando comentarios de ejemplo...')
        
        # Obtener algunas tareas para comentar
        tasks = Task.objects.all()[:3]
        
        comments_data = [
            {
                'text': '¡Excelente trabajo en el análisis! Los requerimientos están muy claros y detallados. Podemos proceder con la siguiente fase.',
                'author': self.pmo_user if self.pmo_user else self.admin_user,
            },
            {
                'text': 'He revisado el diseño de la base de datos y me parece muy sólido. Solo sugiero añadir un índice en la tabla de productos para mejorar el performance.',
                'author': self.dev_senior if self.dev_senior else self.admin_user,
            },
            {
                'text': 'Necesito aclarar algunos puntos sobre la integración con la API externa. ¿Podríamos tener una reunión esta semana?',
                'author': self.dev_junior if self.dev_junior else self.admin_user,
            },
        ]
        
        for i, task in enumerate(tasks):
            if i < len(comments_data):
                comment_data = comments_data[i]
                comment, created = Comment.objects.get_or_create(
                    task=task,
                    author=comment_data['author'],
                    text=comment_data['text']
                )
                if created:
                    self.stdout.write(f'   ✓ Comentario creado en: {task.title}')

    def print_summary(self):
        """Imprimir resumen de datos creados"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE DATOS DE PRUEBA CREADOS'))
        self.stdout.write('='*60)
        
        # Contar elementos
        users_count = User.objects.count()
        workspaces_count = Workspace.objects.count()
        projects_count = Project.objects.count()
        tasks_count = Task.objects.count()
        roles_count = Role.objects.count()
        comments_count = Comment.objects.count()
        
        self.stdout.write(f'👥 Usuarios: {users_count}')
        self.stdout.write(f'🏢 Workspaces: {workspaces_count}')
        self.stdout.write(f'📁 Proyectos: {projects_count}')
        self.stdout.write(f'📝 Tareas: {tasks_count}')
        self.stdout.write(f'🎭 Roles: {roles_count}')
        self.stdout.write(f'💬 Comentarios: {comments_count}')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🔑 CREDENCIALES DE ACCESO'))
        self.stdout.write('='*60)
        
        # Mostrar credenciales existentes
        if self.admin_user:
            self.stdout.write(f'👑 ADMIN: {self.admin_user.email} / admin123')
        if self.pmo_user:
            self.stdout.write('📊 PMO: pmo@nexuspm.com / pmo123')
        if self.dev_senior:
            self.stdout.write('💻 DEV SENIOR: dev.senior@nexuspm.com / dev123')
        if self.dev_junior:
            self.stdout.write('🌱 DEV JUNIOR: dev.junior@nexuspm.com / dev123')
        if self.designer:
            self.stdout.write('🎨 DISEÑADOR: designer@nexuspm.com / design123')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🚀 ¡TODO LISTO! Ve a http://localhost:8000/ para explorar'))
        self.stdout.write('='*60)
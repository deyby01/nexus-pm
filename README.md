# Nexus PM 📝

Una aplicación web completa para la gestión de proyectos, tareas y equipos, construida con Django y diseñada para ser una herramienta profesional, escalable y con una experiencia de usuario moderna.

![Screenshot de Nexus PM](https://i.imgur.com/3ddf1f.png)

---

## 🚀 Acerca del Proyecto

**Nexus PM** nació como un proyecto avanzado para profundizar en las capacidades de Django y construir una aplicación de nivel empresarial desde cero. El objetivo no era solo crear una lista de tareas, sino una plataforma colaborativa completa que resolviera problemas reales de la gestión de proyectos, como la visualización de dependencias, la gestión de roles y la automatización de flujos de trabajo.

Este repositorio sirve como una demostración de habilidades en desarrollo backend, arquitectura de software, diseño de UX/UI y la implementación de funcionalidades complejas.

---

## 🛠️ Stack Tecnológico

La aplicación está construida con un conjunto de herramientas modernas y robustas:

* **Backend:**
    * **Python 3.11+**
    * **Django 5+**: El núcleo de la aplicación.
    * **PostgreSQL**: Para una base de datos relacional robusta.
* **Frontend:**
    * **HTML5 / CSS3**
    * **Bootstrap 5**: Para un diseño responsive y componentes de UI modernos.
    * **JavaScript (ES6+)**: Para la interactividad del lado del cliente.
    * **htmx**: Para crear una experiencia de usuario altamente dinámica y reactiva sin necesidad de un framework de JavaScript pesado.
* **Librerías Clave de Python:**
    * `django-allauth`: Para un sistema de autenticación completo (local y social).
    * `python-dotenv`: Para la gestión segura de variables de entorno.
* **Librerías Clave de JavaScript:**
    * `SortableJS`: Para la funcionalidad de arrastrar y soltar (Drag and Drop) en el tablero Kanban.
    * `Chart.js`: Para la visualización de datos en reportes.
    * `Frappe-Gantt`: Para la creación de cronogramas y diagramas de Gantt interactivos.

---

## ✨ Funcionalidades Implementadas

#### Gestión de Proyectos y Tareas
* ✅ **Workspaces Colaborativos**: Creación de equipos para agrupar proyectos y miembros.
* ✅ **Gestión de Proyectos**: Creación y visualización de proyectos dentro de un workspace.
* ✅ **Tablero Kanban Interactivo**: Visualización de tareas por estado con funcionalidad de **arrastrar y soltar** para cambiar el estado.
* ✅ **Creación y Edición en Modales**: Interfaz fluida (impulsada por htmx) para crear y editar tareas sin recargar la página.
* ✅ **Prioridades y Dependencias**: Asignación de prioridad a las tareas y definición de predecesoras para un flujo de trabajo lógico.
* ✅ **Bloqueo por Dependencias**: El sistema impide iniciar una tarea si sus predecesoras no están completadas.

#### Colaboración y Roles
* ✅ **Sistema de Invitaciones**: Los dueños de workspaces pueden invitar a nuevos miembros a través de enlaces únicos y seguros.
* ✅ **Roles y Permisos Dinámicos**: Sistema flexible donde los administradores pueden **crear y asignar roles personalizados** (PMO, Desarrollador, etc.).
* ✅ **Lógica de Permisos**: La interfaz se adapta, ocultando/mostrando opciones según el rol del usuario (ej: solo los dueños pueden crear proyectos o gestionar el equipo).
* ✅ **Comentarios y Archivos Adjuntos**: Hilo de comentarios en cada tarea con capacidad para subir múltiples archivos.

#### Productividad y Automatización
* ✅ **Registro de Tiempo (Time Tracking)**: Cronómetro en vivo para registrar el tiempo dedicado a cada tarea.
* ✅ **Automatizaciones Básicas**: Creación de comentarios automáticos cuando una tarea se marca como completada.

#### Reportería y Visualización
* ✅ **Dashboard Dinámico**: La vista principal cambia según el rol del usuario (vista de PMO vs. vista de Desarrollador).
* ✅ **Salud del Proyecto**: Indicadores visuales que muestran si un proyecto está "En Plazo", "En Riesgo" o "Vencido".
* ✅ **Gráficos e Informes**: Página de reportes con gráficos de pie (distribución de tareas) y de barras (carga de trabajo por usuario).
* ✅ **Diagrama de Gantt**: Vista de cronograma interactiva que muestra la duración de las tareas y sus dependencias con flechas.

---

## 🧠 Conceptos Avanzados Aplicados

* **Arquitectura Orientada a Componentes con HTMX**: Se utilizaron plantillas parciales y swaps "Out-of-Band" (OOB) para crear una experiencia de usuario reactiva sin un framework de frontend pesado.
* **Migraciones de Datos**: Se implementó una migración de datos personalizada para poblar la base de datos con roles por defecto.
* **Consultas Complejas a la BD**: Uso de `annotate`, `Q objects` y optimización de consultas para generar los datos de los reportes y filtros.
* **Programación Asíncrona Simulada**: La lógica de notificaciones y actividades está diseñada para ser fácilmente transferible a un sistema de colas de tareas como Celery.
* **Testing y Depuración Avanzada**: Resolución de problemas complejos de JavaScript (scope, timing, carga de módulos) y de CSS (conflictos de especificidad).

---
*Este proyecto fue desarrollado con la guía y mentoría de un asistente de IA de Google.*
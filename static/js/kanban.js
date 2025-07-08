document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    const kanbanBoard = document.querySelector('.kanban-board');
    // --- INICIO DEL CÓDIGO DE DEPURACIÓN ---
    console.log("Elemento .kanban-board encontrado:", kanbanBoard);
    if (kanbanBoard) {
        console.log("URL leída desde data-update-url:", kanbanBoard.dataset.updateUrl);
    } else {
        console.error("¡ERROR CRÍTICO! No se pudo encontrar el elemento <div class='kanban-board'>");
    }
    // --- FIN DE LA DEPURACIÓN ---
    const updateUrl = kanbanBoard.dataset.updateUrl;
    const taskContainers = document.querySelectorAll('.tasks-container');

    taskContainers.forEach(container => {
        new Sortable(container, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'ghost',
            onEnd: function (evt) {
                const taskCard = evt.item;
                const newContainer = evt.to;
                const taskId = taskCard.id.replace('task-', '');
                const newStatus = newContainer.dataset.status;

                const params = {
                    task_id: taskId,
                    new_status: newStatus
                };

                htmx.ajax('POST', updateUrl, {
                    values: params,
                    headers: {'X-CSRFToken': csrfToken},
                    swap: 'none'
                }).then(() => {
                    console.log(`Tarea ${taskId} movida a ${newStatus}. ¡Guardado!`);
                }).catch(error => {
                    console.error("Error al actualizar la tarea:", error);
                });
            }
        });
    });
});
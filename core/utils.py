def can_user_interact_with_project(project, user):
    """ 
    Verifica si un usuario puede interactuar (modificar) con un proyecto.
    Retorna True si el proyecto no esta vencido, o si el usuario es el dueño.
    """
    is_owner = (user == project.workspace.owner)
    is_expired = (project.health_status == 'Vencido')
    
    if is_expired and not is_owner:
        return False
    
    return True
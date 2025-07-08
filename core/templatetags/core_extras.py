from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.simple_tag(takes_context=True)
def unread_notifications_count(context):
    """ Obtiene el numero de notificaciones no leídas del usuario actual. """
    request = context.get('request')
    if request and request.user.is_authenticated:
        return request.user.notifications.filter(read=False).count()
    return 0
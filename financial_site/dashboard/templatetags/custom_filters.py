from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except (AttributeError, TypeError):
        return None  # безопасно вернёт None, если d не словарь

@register.filter
def multiply(value, arg):
    try:
        return round(float(value) * float(arg), 2)
    except (TypeError, ValueError):
        return ''

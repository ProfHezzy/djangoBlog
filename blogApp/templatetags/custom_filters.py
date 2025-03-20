from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key, None)

@register.filter(name='add_attributes')
def add_attributes(field, attrs):
    """Adds attributes to a form field."""
    parts = attrs.split(',')
    try:
        for part in parts:
            k, v = part.split(':', 1)
            field.field.widget.attrs[k.strip()] = v.strip()
        return field
    except ValueError:
        return field
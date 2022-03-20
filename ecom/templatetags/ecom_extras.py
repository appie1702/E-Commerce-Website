from django import template

register = template.Library()


@register.filter(name="get_key_value")
def get_key_value(some_dict, key):
    return some_dict.get(key, '')

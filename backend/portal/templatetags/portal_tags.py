from django import template

register = template.Library()


@register.simple_tag
def nav_active(request, *url_names: str) -> str:
    name = getattr(getattr(request, "resolver_match", None), "url_name", None) or ""
    return " is-active" if name in url_names else ""


@register.simple_tag
def query_transform(request, **kwargs):
    """GET parametrlərini saxlayaraq `page` və s. dəyişmək üçün."""
    q = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            q.pop(key, None)
        elif value == "":
            q.pop(key, None)
        else:
            q[key] = str(value)
    return q.urlencode()

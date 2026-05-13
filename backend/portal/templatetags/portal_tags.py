from django import template

register = template.Library()


@register.simple_tag
def nav_active(request, *url_names: str) -> str:
    name = getattr(getattr(request, "resolver_match", None), "url_name", None) or ""
    return " is-active" if name in url_names else ""


@register.simple_tag(takes_context=True)
def query_transform(context, request, **kwargs):
    """GET parametrlərini saxlayaraq `page` və s. dəyişmək üçün; URL-də ``ay`` yoxdursa cari portal ili əlavə olunur."""
    q = request.GET.copy()
    ay_ctx = context.get("portal_academic_year_start")
    if ay_ctx is not None and "ay" not in q and "ay" not in kwargs:
        q["ay"] = str(int(ay_ctx))
    for key, value in kwargs.items():
        if value is None:
            q.pop(key, None)
        elif value == "":
            q.pop(key, None)
        else:
            q[key] = str(value)
    return q.urlencode()

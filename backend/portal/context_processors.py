from django.conf import settings

from portal.academic_year import (
    academic_year_choice_years,
    academic_year_label,
    resolve_portal_academic_year_start,
)


def portal_academic_year(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    y = resolve_portal_academic_year_start(request)
    return {
        "portal_academic_year_start": y,
        "portal_academic_year_label": academic_year_label(y),
        "portal_academic_year_choices": academic_year_choice_years(y),
    }


def portal_database_notice(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.is_staff:
        return {}
    if not getattr(settings, "PORTAL_EPHEMERAL_DATABASE", False):
        return {}
    return {"portal_db_ephemeral_warning": True}

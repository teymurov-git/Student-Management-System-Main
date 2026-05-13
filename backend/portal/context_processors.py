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

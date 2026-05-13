"""Portal üçün tədris ili (1 Sentyabr başlanğıc ili) seçimi və sessiya."""

from __future__ import annotations

SESSION_KEY = "portal_academic_year_start"
YEAR_MIN = 2000
YEAR_MAX = 2100


def resolve_portal_academic_year_start(request) -> int:
    """GET/POST ``ay`` ilə sessiyanı yeniləyir; yoxdursa sessiya və ya cari tədris ili."""
    from portal.services.income import current_academic_year_start

    default_y = current_academic_year_start().year
    raw = ""
    if getattr(request, "GET", None):
        raw = (request.GET.get("ay") or "").strip()
    if not raw and getattr(request, "POST", None):
        raw = (request.POST.get("ay") or "").strip()
    if raw.isdigit():
        y = int(raw)
        if YEAR_MIN <= y <= YEAR_MAX:
            request.session[SESSION_KEY] = y
            return y

    stored = request.session.get(SESSION_KEY)
    if isinstance(stored, int) and YEAR_MIN <= stored <= YEAR_MAX:
        return stored
    if isinstance(stored, str) and stored.strip().isdigit():
        y = int(stored.strip())
        if YEAR_MIN <= y <= YEAR_MAX:
            return y

    request.session[SESSION_KEY] = default_y
    return default_y


def academic_year_label(start_year: int) -> str:
    return f"{start_year}–{start_year + 1}"


def academic_year_choice_years(center: int, past: int = 4, future: int = 6) -> list[int]:
    try:
        c = int(center)
    except (TypeError, ValueError):
        c = YEAR_MIN
    c = max(YEAR_MIN, min(YEAR_MAX, c))
    lo = max(YEAR_MIN, c - past)
    hi = min(YEAR_MAX, c + future)
    years = list(range(lo, hi + 1))
    if not years:
        years = [c]
    return years

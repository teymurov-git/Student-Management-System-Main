"""Portal üçün əlavə middleware (tədris ili güzgüsü)."""

from __future__ import annotations

from portal.academic_year import COOKIE_NAME, resolve_portal_academic_year_start


class PortalAcademicYearCookieMiddleware:
    """
    Seçilmiş tədris ilini uzunömürlü cookie-də saxlayır.

    Sessiya (xüsusən serverless və ya yeni deploy) sıfırlananda brauzerdəki
    ``portal_ay`` dəyəri ``resolve_portal_academic_year_start`` tərəfindən
    oxunur və sessiya bərpa olunur.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return response
        y = resolve_portal_academic_year_start(request)
        response.set_cookie(
            COOKIE_NAME,
            str(int(y)),
            max_age=60 * 60 * 24 * 400,
            httponly=True,
            samesite="Lax",
            secure=request.is_secure(),
        )
        return response

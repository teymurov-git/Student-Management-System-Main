"""Tədris ili (ay) sessiya + cookie davamlılığı və query_transform."""

from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from portal.academic_year import COOKIE_NAME, SESSION_KEY, resolve_portal_academic_year_start


def _add_session(request):
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()


class AcademicYearPersistenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="x")

    def test_cookie_restores_year_when_session_empty(self):
        rf = RequestFactory()
        request = rf.get("/")
        request.user = self.user
        request.session = {}
        request.COOKIES[COOKIE_NAME] = "2024"
        y = resolve_portal_academic_year_start(request)
        self.assertEqual(y, 2024)
        self.assertEqual(request.session[SESSION_KEY], 2024)

    def test_get_ay_overrides_cookie(self):
        rf = RequestFactory()
        request = rf.get("/", data={"ay": "2026"})
        _add_session(request)
        request.user = self.user
        request.COOKIES[COOKIE_NAME] = "2024"
        y = resolve_portal_academic_year_start(request)
        self.assertEqual(y, 2026)

    def test_query_transform_adds_ay_from_context(self):
        rf = RequestFactory()
        request = rf.get("/students/", data={"q": "Ali"})
        tpl = Template(
            "{% load portal_tags %}"
            "{% url 'portal:student_list' as u %}"
            "{{ u }}?{% query_transform request %}"
        )
        html = tpl.render(Context({"request": request, "portal_academic_year_start": 2025}))
        self.assertIn("ay=2025", html)
        self.assertIn("q=Ali", html)


class PortalAcademicYearCookieMiddlewareTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u2", password="y")

    def test_middleware_sets_portal_ay_cookie(self):
        from portal.middleware import PortalAcademicYearCookieMiddleware

        rf = RequestFactory()
        request = rf.get("/portal/", data={"ay": "2023"})
        request.user = self.user
        _add_session(request)
        resolve_portal_academic_year_start(request)

        def view(req):
            from django.http import HttpResponse

            return HttpResponse("ok")

        mw = PortalAcademicYearCookieMiddleware(view)
        response = mw(request)
        self.assertEqual(response.cookies[COOKIE_NAME].value, "2023")

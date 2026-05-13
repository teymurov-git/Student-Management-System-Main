"""Portal tələbə formu: tədris ili ilə qrup uyğunluğu (regressiya)."""

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from portal.forms import StudentForm, build_student_group_quick_form
from students.models import Student, StudentGroup


def _add_session(request):
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()


class StudentFormAcademicYearRegressionTests(TestCase):
    def setUp(self):
        self.group = StudentGroup.objects.create(
            name="Online 1",
            academic_year_start=2026,
            monthly_fee=100,
        )

    def test_create_student_form_matches_portal_year_before_model_clean(self):
        """``academic_year_start`` Meta.fields-də olmadığı halda ``Student.clean`` ili gözləyir."""
        data = {
            "first_name": "A",
            "last_name": "B",
            "father_name": "",
            "phone": "1",
            "parent_phone": "",
            "student_group": str(self.group.pk),
            "monthly_tuition": "0",
            "registration_date": "2026-05-01",
            "status": Student.Status.ACTIVE,
            "notes": "",
        }
        form = StudentForm(data=data, academic_year_start=2026)
        self.assertTrue(form.is_valid(), msg=form.errors)
        student = form.save(commit=False)
        self.assertEqual(student.academic_year_start, 2026)
        self.assertEqual(student.student_group_id, self.group.pk)

    def test_quick_group_form_defaults_academic_year_to_portal_session(self):
        rf = RequestFactory()
        request = rf.get("/", data={"ay": "2026"})
        _add_session(request)
        form = build_student_group_quick_form(request)
        self.assertFalse(form.is_bound)
        self.assertEqual(form.initial.get("academic_year_start"), 2026)

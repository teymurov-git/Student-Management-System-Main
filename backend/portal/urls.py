from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("login/", views.PortalLoginView.as_view(), name="login"),
    path("logout/", views.PortalLogoutView.as_view(), name="logout"),
    path("students/", views.StudentListView.as_view(), name="student_list"),
    path(
        "students/bulk-archive/",
        views.StudentBulkArchiveView.as_view(),
        name="student_bulk_archive",
    ),
    path(
        "students/bulk-archive-filtered/",
        views.StudentBulkArchiveFilteredView.as_view(),
        name="student_bulk_archive_filtered",
    ),
    path(
        "students/groups/<int:pk>/archive-students/",
        views.StudentBulkArchiveGroupView.as_view(),
        name="student_bulk_archive_group",
    ),
    path("students/groups/", views.StudentGroupListView.as_view(), name="student_group_list"),
    path("students/groups/add/", views.StudentGroupCreateView.as_view(), name="student_group_add"),
    path(
        "students/groups/<int:pk>/edit/",
        views.StudentGroupUpdateView.as_view(),
        name="student_group_edit",
    ),
    path(
        "students/groups/<int:pk>/delete/",
        views.StudentGroupDeleteView.as_view(),
        name="student_group_delete",
    ),
    path("students/add/", views.StudentCreateView.as_view(), name="student_add"),
    path("students/<int:pk>/", views.StudentDetailView.as_view(), name="student_detail"),
    path("students/<int:pk>/edit/", views.StudentUpdateView.as_view(), name="student_edit"),
    path("students/<int:pk>/archive/", views.StudentArchiveView.as_view(), name="student_archive"),
    path("davamiyyet/", views.AttendanceListView.as_view(), name="attendance_list"),
    path("davamiyyet/add/", views.AttendanceMarkView.as_view(), name="attendance_add"),
    path("odenisler/", views.PaymentYearGridView.as_view(), name="payment_grid"),
    path("odenisler/set-status/", views.PaymentSetStatusView.as_view(), name="payment_set_status"),
    path("payments/", views.PaymentListView.as_view(), name="payment_list"),
    path("payments/add/", views.PaymentCreateView.as_view(), name="payment_add"),
    path("payments/<int:pk>/edit/", views.PaymentUpdateView.as_view(), name="payment_edit"),
    path("export/students.xlsx", views.ExportStudentsXlsxView.as_view(), name="export_students_xlsx"),
    path("export/students.pdf", views.ExportStudentsPdfView.as_view(), name="export_students_pdf"),
    path("export/payments.xlsx", views.ExportPaymentsXlsxView.as_view(), name="export_payments_xlsx"),
]

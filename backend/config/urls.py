from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import DashboardView, HealthView, PaymentRemindersView

urlpatterns = [
    path("", include("portal.urls")),
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view()),
    path("api/auth/token/", TokenObtainPairView.as_view()),
    path("api/auth/token/refresh/", TokenRefreshView.as_view()),
    path("api/dashboard/", DashboardView.as_view()),
    path("api/reminders/payments/", PaymentRemindersView.as_view()),
    path("api/", include("students.urls")),
    path("api/", include("payments.urls")),
    path("api/", include("attendance.urls")),
    path("api/", include("exams.urls")),
    path("api/", include("audit.urls")),
]

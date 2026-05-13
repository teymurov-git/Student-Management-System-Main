from datetime import date

from django.db.models import Sum
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from payments.models import MonthlyPayment
from portal.services.income import current_academic_year_start
from students.models import Student
from students.serializers import StudentSerializer


def _api_academic_year_start(request) -> int:
    raw = request.query_params.get("academic_year_start")
    if raw is not None and str(raw).strip().isdigit():
        return int(str(raw).strip())
    return current_academic_year_start().year


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today_d = date.today()
        ay = _api_academic_year_start(request)
        active_students = Student.objects.filter(
            is_archived=False,
            status=Student.Status.ACTIVE,
            academic_year_start=ay,
        ).count()

        recent_students = Student.objects.filter(
            is_archived=False, academic_year_start=ay
        ).order_by("-created_at")[:8]

        revenue = MonthlyPayment.objects.filter(
            year=today_d.year,
            month=today_d.month,
            status=MonthlyPayment.Status.PAID,
        ).aggregate(t=Sum("amount"))["t"]
        revenue_f = float(revenue) if revenue is not None else 0.0

        return Response(
            {
                "academic_year_start": ay,
                "active_students": active_students,
                "recent_students": StudentSerializer(recent_students, many=True).data,
                "month_revenue": revenue_f,
            }
        )


class PaymentRemindersView(APIView):
    """Cari ay üçün ödənməyən / gecikən qeydlər (bildiriş siyahısı)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        today_d = date.today()
        ay = _api_academic_year_start(request)
        qs = MonthlyPayment.objects.select_related("student").filter(
            year=today_d.year,
            month=today_d.month,
            status__in=[
                MonthlyPayment.Status.UNPAID,
                MonthlyPayment.Status.LATE,
            ],
            student__academic_year_start=ay,
        )
        items = [
            {
                "student_id": p.student_id,
                "student_name": p.student.full_name,
                "parent_phone": p.student.parent_phone,
                "phone": p.student.phone,
                "amount": str(p.amount),
                "status": p.status,
            }
            for p in qs[:200]
        ]
        return Response({"count": len(items), "items": items, "academic_year_start": ay})


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})

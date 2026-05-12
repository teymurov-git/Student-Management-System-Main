from datetime import date

from django.db.models import Sum
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from payments.models import MonthlyPayment
from students.models import Student
from students.serializers import StudentSerializer


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today_d = date.today()
        active_students = Student.objects.filter(
            is_archived=False, status=Student.Status.ACTIVE
        ).count()

        recent_students = Student.objects.filter(is_archived=False).order_by(
            "-created_at"
        )[:8]

        revenue = MonthlyPayment.objects.filter(
            year=today_d.year,
            month=today_d.month,
            status=MonthlyPayment.Status.PAID,
        ).aggregate(t=Sum("amount"))["t"]
        revenue_f = float(revenue) if revenue is not None else 0.0

        return Response(
            {
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
        qs = MonthlyPayment.objects.select_related("student").filter(
            year=today_d.year,
            month=today_d.month,
            status__in=[
                MonthlyPayment.Status.UNPAID,
                MonthlyPayment.Status.LATE,
            ],
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
        return Response({"count": len(items), "items": items})


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})

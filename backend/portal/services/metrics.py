"""Dashboard və qısa statistikalar (view-lərdən ayrılmış biznes məntiqi)."""
from datetime import date

from django.db.models import Sum

from payments.models import MonthlyPayment
from students.models import Student

from .income import (
    academic_year_forecast_total,
    current_academic_year_start,
    expected_monthly_tuition_total,
    group_forecast_breakdown,
)


def get_dashboard_context(academic_year_start: int) -> dict:
    today_d = date.today()
    active_students = Student.objects.filter(
        is_archived=False,
        status=Student.Status.ACTIVE,
        academic_year_start=academic_year_start,
    ).count()
    recent_students = list(
        Student.objects.filter(
            is_archived=False, academic_year_start=academic_year_start
        )
        .select_related("student_group")
        .order_by("-created_at")[:8]
    )
    rev = MonthlyPayment.objects.filter(
        year=today_d.year,
        month=today_d.month,
        status=MonthlyPayment.Status.PAID,
    ).aggregate(t=Sum("amount"))["t"]
    month_revenue = float(rev) if rev is not None else 0.0
    yearly_rev_agg = MonthlyPayment.objects.filter(
        year=today_d.year,
        status=MonthlyPayment.Status.PAID,
    ).aggregate(t=Sum("amount"))["t"]
    yearly_revenue_paid = float(yearly_rev_agg) if yearly_rev_agg is not None else 0.0

    teaching_forecast_dec = academic_year_forecast_total(academic_year_start)
    teaching_forecast = float(teaching_forecast_dec)
    monthly_forecast = float(expected_monthly_tuition_total(academic_year_start))

    ay_start = current_academic_year_start(today_d)
    group_income_rows = group_forecast_breakdown(
        ay_start, roster_academic_year_start=academic_year_start
    )

    return {
        "today": today_d,
        "active_students": active_students,
        "recent_students": recent_students,
        "month_revenue": month_revenue,
        "monthly_forecast": monthly_forecast,
        "yearly_revenue_paid": yearly_revenue_paid,
        "yearly_forecast": teaching_forecast,
        "teaching_forecast": teaching_forecast,
        "group_income_rows": group_income_rows,
    }

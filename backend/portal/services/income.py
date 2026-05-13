"""Ödəniş cədvəli üçün cəm məntiqi."""

from datetime import date
from decimal import Decimal
from typing import Optional

from django.db.models import Q, Sum

from payments.models import MonthlyPayment
from students.models import Student


# Tədris ili: 1 Sentyabr ildə Y-dən 31 Avqust Y+1-ə qədər (12 ay)
ACADEMIC_YEAR_START_MONTH = 9
ACADEMIC_YEAR_MONTHS = 12


def paid_amount_for_month(year: int, month: int) -> Decimal:
    agg = MonthlyPayment.objects.filter(
        year=year,
        month=month,
        status=MonthlyPayment.Status.PAID,
    ).aggregate(t=Sum("amount"))["t"]
    return agg if agg is not None else Decimal("0")


def paid_amount_for_year(year: int) -> Decimal:
    agg = MonthlyPayment.objects.filter(
        year=year,
        status=MonthlyPayment.Status.PAID,
    ).aggregate(t=Sum("amount"))["t"]
    return agg if agg is not None else Decimal("0")


def current_academic_year_start(today: Optional[date] = None) -> date:
    """İndiki tədris ilinin ilk günü: 1 Sentyabr.

    Bu günün ayı ≥ 9 olarsa — həmin təqvim ilinin 1 Sentyabrı; əks halda əvvəlki ilin 1 Sentyabrı
    (məs. 2026 fevral → 2025-09-01).
    """
    d = today or date.today()
    y = d.year if d.month >= ACADEMIC_YEAR_START_MONTH else d.year - 1
    return date(y, ACADEMIC_YEAR_START_MONTH, 1)


def academic_year_month_pairs(academic_year_start: date) -> list[tuple[int, int]]:
    """Cari tədris ili üçün 12 (il, ay): Sentyabr–Dekabr başlanğıc ili, Yanvar–Avqust növbəti il.

    ``academic_year_start`` adətən ``current_academic_year_start()`` nəticəsi (1 Sentyabr) olur.
    """
    y = academic_year_start.year
    return [(y, m) for m in range(9, 13)] + [(y + 1, m) for m in range(1, 9)]


def _academic_year_payments_filter(academic_year_start: date) -> Q:
    q = Q()
    for ym in academic_year_month_pairs(academic_year_start):
        q |= Q(year=ym[0], month=ym[1])
    return q


def expected_monthly_tuition_total(academic_year_start: int | None = None) -> Decimal:
    """Aktiv, arxivdə olmayan tələbələr üçün effektiv aylıq ödənişlərin bir aylıq cəmi Σ."""
    total = Decimal("0")
    qs = Student.objects.filter(
        is_archived=False, status=Student.Status.ACTIVE
    ).select_related("student_group")
    if academic_year_start is not None:
        qs = qs.filter(academic_year_start=academic_year_start)
    for s in qs:
        total += s.effective_monthly_fee()
    return total


def academic_year_forecast_total(academic_year_start: int | None = None) -> Decimal:
    """Tam tədris ili (12 ay, Sentyabr–Avqust) üçün proqnoz: Σ (effektiv aylıq) × 12."""
    return expected_monthly_tuition_total(academic_year_start) * ACADEMIC_YEAR_MONTHS


def group_forecast_breakdown(
    academic_year_start_date: date,
    roster_academic_year_start: int | None = None,
) -> list[dict]:
    """Hər qrup üçün aylıq proqnoz, cari tədris ili (Sent–Avq) üzrə ödənib cəmi, 12 aylıq proqnoz.

    Boş aktiv tələbəli qruplar siyahıda göstərilmir.
    """
    active = Student.objects.filter(
        is_archived=False,
        status=Student.Status.ACTIVE,
        student_group__isnull=False,
    ).select_related("student_group")
    if roster_academic_year_start is not None:
        active = active.filter(academic_year_start=roster_academic_year_start)

    monthly_by_group: dict[int, Decimal] = {}
    group_labels: dict[int, str] = {}
    student_ids_by_group: dict[int, list[int]] = {}

    for s in active:
        gid = s.student_group_id
        assert gid is not None
        group_labels.setdefault(gid, s.student_group.name)
        monthly_by_group[gid] = monthly_by_group.get(gid, Decimal("0")) + s.effective_monthly_fee()
        student_ids_by_group.setdefault(gid, []).append(s.pk)

    if not monthly_by_group:
        return []

    month_filter = _academic_year_payments_filter(academic_year_start_date)

    rows: list[dict] = []
    for gid in sorted(monthly_by_group.keys(), key=lambda i: group_labels[i].lower()):
        student_ids = student_ids_by_group[gid]
        paid_agg = (
            MonthlyPayment.objects.filter(
                month_filter,
                status=MonthlyPayment.Status.PAID,
                student_id__in=student_ids,
            )
            .aggregate(t=Sum("amount"))["t"]
        )
        paid_total = paid_agg if paid_agg is not None else Decimal("0")
        monthly = monthly_by_group[gid]
        rows.append(
            {
                "group_id": gid,
                "group_name": group_labels[gid],
                "monthly_forecast_azn": monthly,
                "academic_year_paid_azn": paid_total,
                "academic_year_forecast_azn": monthly * ACADEMIC_YEAR_MONTHS,
            }
        )
    return rows


def student_paid_totals(student_id: int, year: int, month: int) -> tuple[Decimal, Decimal]:
    monthly = MonthlyPayment.objects.filter(
        student_id=student_id,
        year=year,
        month=month,
        status=MonthlyPayment.Status.PAID,
    ).aggregate(t=Sum("amount"))["t"]
    yearly = MonthlyPayment.objects.filter(
        student_id=student_id,
        year=year,
        status=MonthlyPayment.Status.PAID,
    ).aggregate(t=Sum("amount"))["t"]
    m = monthly if monthly is not None else Decimal("0")
    y = yearly if yearly is not None else Decimal("0")
    return m, y

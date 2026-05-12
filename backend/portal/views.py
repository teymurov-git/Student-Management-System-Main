import calendar
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from attendance.models import AttendanceRecord
from audit.utils import log_audit
from payments.models import MonthlyPayment
from students.models import Student, StudentGroup


def student_list_filtered_qs(params):
    """URL GET və ya POST (gizli parametrlərlə eyni açarlar) üçün ümumi filtr."""
    qs = Student.objects.select_related("student_group").all()
    if params.get("archived") != "1":
        qs = qs.filter(is_archived=False)
    q = params.get("q", "")
    q = q.strip() if isinstance(q, str) else ""
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(phone__icontains=q)
            | Q(class_group__icontains=q)
        )
    cg = params.get("class_group", "")
    cg = cg.strip() if isinstance(cg, str) else ""
    if cg:
        qs = qs.filter(class_group=cg)
    gid_raw = params.get("student_group", "")
    gid = gid_raw.strip() if isinstance(gid_raw, str) else str(gid_raw)
    if gid.isdigit():
        qs = qs.filter(student_group_id=int(gid))
    return qs


from .forms import (
    MonthlyPaymentForm,
    PortalAuthenticationForm,
    StudentForm,
    StudentGroupForm,
    StudentGroupQuickForm,
)
from .services.income import (
    paid_amount_for_month,
    paid_amount_for_year,
    student_paid_totals,
)
from .services.metrics import get_dashboard_context

AZ_MONTHS = (
    "",
    "Yanvar",
    "Fevral",
    "Mart",
    "Aprel",
    "May",
    "İyun",
    "İyul",
    "Avqust",
    "Sentyabr",
    "Oktyabr",
    "Noyabr",
    "Dekabr",
)

# Qısa ay etiketləri; indeks təqvim ay nömrəsi (1=Yan, …, 12=Dek).
AZ_MONTH_SHORT = (
    "",
    "Yan",
    "Fev",
    "Mar",
    "Apr",
    "May",
    "İyn",
    "İyl",
    "Avq",
    "Sen",
    "Okt",
    "Noy",
    "Dek",
)

# Cədvəldə tədris ili sırası: Sentyabr → növbəti il Avqust (təqvim ay nömrələri).
PAYMENT_GRID_MONTH_ORDER = (9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8)

ATTENDANCE_MARK_STATUSES = (
    (AttendanceRecord.Status.PRESENT, "İştirak etdi"),
    (AttendanceRecord.Status.ABSENT, "İştirak etmədi"),
    (AttendanceRecord.Status.LATE, "Gecikdi"),
)
ATTENDANCE_STATUS_LABELS = {
    **dict(AttendanceRecord.Status.choices),
    **dict(ATTENDANCE_MARK_STATUSES),
}
ATTENDANCE_STATUS_META = {
    AttendanceRecord.Status.PRESENT: {
        "icon": "✓",
        "css": "badge-ok",
        "label": "İştirak etdi",
    },
    AttendanceRecord.Status.ABSENT: {
        "icon": "✕",
        "css": "badge-bad",
        "label": "İştirak etmədi",
    },
    AttendanceRecord.Status.LATE: {
        "icon": "!",
        "css": "badge-warn",
        "label": "Gecikdi",
    },
}
ATTENDANCE_STATUS_OPTIONS = [
    {
        "value": value,
        "label": ATTENDANCE_STATUS_META[value]["label"],
        "icon": ATTENDANCE_STATUS_META[value]["icon"],
        "css": ATTENDANCE_STATUS_META[value]["css"],
    }
    for value, _label in ATTENDANCE_MARK_STATUSES
]


def _safe_next_url(request):
    next_url = (request.POST.get("next") or "").strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return None


def _parse_attendance_date(raw):
    try:
        return date.fromisoformat((raw or "").strip())
    except (TypeError, ValueError):
        return date.today()


def _parse_iso_date(value, fallback=None):
    fallback = fallback or date.today()
    try:
        return date.fromisoformat((value or "").strip())
    except (TypeError, ValueError):
        return fallback


def _parse_month(value, fallback=None):
    fallback = fallback or date.today()
    raw = (value or "").strip()
    try:
        year_s, month_s = raw.split("-", 1)
        year, month = int(year_s), int(month_s)
        if 1 <= month <= 12:
            return year, month
    except (TypeError, ValueError):
        pass
    return fallback.year, fallback.month


def _month_value(year, month):
    return f"{year:04d}-{month:02d}"


def _attendance_redirect(group_id, target_date, month_value):
    return redirect(
        reverse("portal:attendance_add")
        + f"?student_group={group_id}&date={target_date.isoformat()}&month={month_value}"
    )


def _attendance_list_redirect(group_id, month_value):
    return redirect(
        reverse("portal:attendance_list") + f"?student_group={group_id}&month={month_value}"
    )


def _lesson_dates_for_month(group, year, month):
    if not group:
        return []
    days_in_month = calendar.monthrange(year, month)[1]
    return [
        date(year, month, day)
        for day in range(1, days_in_month + 1)
        if group.is_lesson_day(date(year, month, day))
    ]


class PortalLoginView(LoginView):
    template_name = "portal/login.html"
    form_class = PortalAuthenticationForm
    redirect_authenticated_user = True


class PortalLogoutView(LogoutView):
    next_page = reverse_lazy("portal:login")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(get_dashboard_context())
        return ctx


class StudentGroupListView(LoginRequiredMixin, ListView):
    model = StudentGroup
    template_name = "portal/student_group_list.html"
    context_object_name = "student_groups"

    def get_queryset(self):
        return StudentGroup.objects.annotate(student_count=Count("students")).order_by(
            "name"
        )


class StudentGroupCreateView(LoginRequiredMixin, CreateView):
    model = StudentGroup
    form_class = StudentGroupForm
    template_name = "portal/student_group_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(
            self.request.user,
            "create",
            "StudentGroup",
            str(self.object.pk),
            {
                "name": self.object.name,
                "monthly_fee": str(self.object.monthly_fee),
                "lesson_weekdays": self.object.lesson_weekdays,
            },
        )
        messages.success(self.request, f"Qrup «{self.object.name}» əlavə olundu.")
        return response

    def form_invalid(self, form):
        next_url = _safe_next_url(self.request)
        if next_url:
            for err in form.errors.values():
                for e in err:
                    messages.error(self.request, str(e))
            return redirect(next_url)
        return super().form_invalid(form)

    def get_success_url(self):
        return _safe_next_url(self.request) or reverse("portal:student_group_list")


class StudentGroupUpdateView(LoginRequiredMixin, UpdateView):
    model = StudentGroup
    form_class = StudentGroupForm
    template_name = "portal/student_group_form.html"

    def form_valid(self, form):
        old_name = StudentGroup.objects.only("name").get(pk=self.object.pk).name
        response = super().form_valid(form)
        synced_count = 0
        if old_name != self.object.name:
            synced_count = Student.objects.filter(student_group=self.object).update(
                class_group=self.object.name,
                updated_at=timezone.now(),
            )
        log_audit(
            self.request.user,
            "update",
            "StudentGroup",
            str(self.object.pk),
            {
                "name": self.object.name,
                "monthly_fee": str(self.object.monthly_fee),
                "lesson_weekdays": self.object.lesson_weekdays,
                "synced_students": synced_count,
            },
        )
        messages.success(self.request, f"Qrup «{self.object.name}» yeniləndi.")
        return response

    def get_success_url(self):
        return reverse("portal:student_group_list")


class StudentGroupDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        group = get_object_or_404(StudentGroup, pk=pk)
        name = group.name
        gid = group.pk
        linked_students = Student.objects.filter(student_group_id=gid)
        student_count = linked_students.count()
        linked_students.update(class_group="", updated_at=timezone.now())
        group.delete()
        log_audit(
            request.user,
            "delete",
            "StudentGroup",
            str(gid),
            {"name": name, "students_unlinked": student_count},
        )
        if student_count:
            messages.success(
                request,
                f"Qrup «{name}» silindi. Bu qrupa bağlı {student_count} tələbənin «Qrup» seçimi təmizləndi.",
            )
        else:
            messages.success(request, f"Qrup «{name}» silindi.")
        next_url = _safe_next_url(request)
        if next_url:
            return redirect(next_url)
        return redirect("portal:student_group_list")


class StudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "portal/student_list.html"
    context_object_name = "students"
    paginate_by = 30

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["class_groups"] = (
            Student.objects.exclude(class_group="")
            .values_list("class_group", flat=True)
            .distinct()
            .order_by("class_group")[:80]
        )
        ctx["student_groups"] = StudentGroup.objects.all().order_by("name")
        ctx["selected_student_group"] = (
            self.request.GET.get("student_group", "").strip() or ""
        )
        sel = ctx["selected_student_group"]
        ctx["bulk_matching_count"] = (
            student_list_filtered_qs(self.request.GET).filter(is_archived=False).count()
        )
        ctx["bulk_group"] = None
        ctx["bulk_group_count"] = 0
        if sel.isdigit():
            g_obj = StudentGroup.objects.filter(pk=int(sel)).first()
            ctx["bulk_group"] = g_obj
            if g_obj:
                ctx["bulk_group_count"] = Student.objects.filter(
                    student_group_id=g_obj.pk, is_archived=False
                ).count()
        ctx["group_form"] = StudentGroupQuickForm()
        return ctx

    def get_queryset(self):
        return student_list_filtered_qs(self.request.GET).order_by("-created_at")


class StudentFormGroupContextMixin:
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["group_form"] = StudentGroupQuickForm()
        return ctx


class StudentCreateView(LoginRequiredMixin, StudentFormGroupContextMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = "portal/student_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        log_audit(
            self.request.user,
            "create",
            "Student",
            str(self.object.pk),
            {k: str(v) for k, v in form.cleaned_data.items()},
        )
        messages.success(self.request, "Tələbə əlavə olundu.")
        return resp

    def get_success_url(self):
        return reverse("portal:student_detail", kwargs={"pk": self.object.pk})


class StudentUpdateView(LoginRequiredMixin, StudentFormGroupContextMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = "portal/student_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        log_audit(
            self.request.user,
            "update",
            "Student",
            str(self.object.pk),
            {k: str(v) for k, v in form.cleaned_data.items()},
        )
        messages.success(self.request, "Yeniləndi.")
        return resp

    def get_success_url(self):
        return reverse("portal:student_detail", kwargs={"pk": self.object.pk})


class StudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = "portal/student_detail.html"
    context_object_name = "student"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        s = self.object
        ctx["payments"] = MonthlyPayment.objects.filter(student=s).order_by(
            "-year", "-month"
        )
        return ctx


class StudentArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        s = get_object_or_404(Student, pk=pk)
        s.is_archived = True
        s.save(update_fields=["is_archived", "updated_at"])
        log_audit(request.user, "update", "Student", str(s.pk), {"is_archived": True})
        messages.info(request, "Arxivləndi.")
        return redirect("portal:student_list")


class StudentBulkArchiveView(LoginRequiredMixin, View):
    """POST ids[] — aktiv tələbələri arxivə (yenidən çıxmaq üçün DB/admin)."""

    def post(self, request):
        raw = request.POST.getlist("ids")
        pks = []
        for x in raw:
            xs = x.strip() if isinstance(x, str) else str(x).strip()
            if xs.isdigit():
                pks.append(int(xs))
        if not pks:
            messages.warning(request, "Heç bir tələbə seçilməyib.")
            return redirect("portal:student_list")

        qs = Student.objects.filter(pk__in=pks, is_archived=False)
        n = qs.update(is_archived=True, updated_at=timezone.now())
        log_audit(
            request.user,
            "bulk_archive",
            "Student",
            "",
            {"count": n, "pk_sample": [str(x) for x in pks[:40]]},
        )
        messages.info(request, f"{n} tələbə arxivə köçürüldü.")
        return redirect("portal:student_list")


class StudentBulkArchiveFilteredView(LoginRequiredMixin, View):
    """
    Hazırkdakı sorğu parametrlərinə uyğun bütün aktiv tələbələri arxivə köçürür
    (səhifələmədən çoxlu sıra üçün).
    """

    def post(self, request):
        qs = student_list_filtered_qs(request.POST).filter(is_archived=False)
        n = qs.update(is_archived=True, updated_at=timezone.now())
        log_audit(
            request.user,
            "bulk_archive_filtered",
            "Student",
            "",
            {"count": n},
        )
        messages.info(request, f"Sorğu üzrə {n} tələbə arxivə köçürüldü.")
        return redirect("portal:student_list")


class StudentBulkArchiveGroupView(LoginRequiredMixin, View):
    def post(self, request, pk):
        group = get_object_or_404(StudentGroup, pk=pk)
        qs = Student.objects.filter(student_group_id=group.pk, is_archived=False)
        n = qs.update(is_archived=True, updated_at=timezone.now())
        log_audit(
            request.user,
            "bulk_archive_group",
            "StudentGroup",
            str(pk),
            {"group_name": group.name, "count": n},
        )
        messages.info(
            request, f"«{group.name}» qrupundan {n} tələbə arxivə köçürüldü."
        )
        next_url = (request.POST.get("next") or "").strip()
        if next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect("portal:student_list")


class AttendanceListView(LoginRequiredMixin, TemplateView):
    template_name = "portal/attendance_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        month_year, month_num = _parse_month(self.request.GET.get("month"), today)
        selected_month = _month_value(month_year, month_num)
        group_id = (self.request.GET.get("student_group") or "").strip()
        selected_group = (
            StudentGroup.objects.filter(pk=int(group_id)).first()
            if group_id.isdigit()
            else None
        )
        lesson_dates = _lesson_dates_for_month(selected_group, month_year, month_num)
        rows = []
        month_stats = []
        marked_count = 0
        attended_count = 0
        expected_count = 0

        if selected_group:
            students = list(
                Student.objects.filter(
                    student_group_id=selected_group.pk,
                    is_archived=False,
                    status=Student.Status.ACTIVE,
                )
                .select_related("student_group")
                .order_by("last_name", "first_name")
            )
            expected_count = len(students) * len(lesson_dates)
            records = list(
                AttendanceRecord.objects.filter(
                    student_id__in=[student.pk for student in students],
                    date__in=lesson_dates,
                ).select_related("student")
            )
            record_map = {
                (record.student_id, record.date): record
                for record in records
            }
            marked_count = len(records)
            attended_count = sum(
                1
                for record in records
                if record.status
                in (AttendanceRecord.Status.PRESENT, AttendanceRecord.Status.LATE)
            )

            for row in (
                AttendanceRecord.objects.filter(
                    student__student_group_id=selected_group.pk,
                    date__year=month_year,
                    date__month=month_num,
                )
                .values("status")
                .annotate(c=Count("id"))
                .order_by("status")
            ):
                meta = ATTENDANCE_STATUS_META.get(row["status"], {})
                row["label"] = ATTENDANCE_STATUS_LABELS.get(row["status"], row["status"])
                row["css"] = meta.get("css", "badge-muted")
                month_stats.append(row)

            for student in students:
                cells = []
                for lesson_date in lesson_dates:
                    record = record_map.get((student.pk, lesson_date))
                    if record:
                        meta = ATTENDANCE_STATUS_META.get(
                            record.status,
                            {
                                "icon": "?",
                                "css": "badge-muted",
                                "label": record.get_status_display(),
                            },
                        )
                        cells.append(
                            {
                                "date": lesson_date,
                                "record": record,
                                "status": record.status,
                                "icon": meta["icon"],
                                "css": meta["css"],
                                "label": meta["label"],
                            }
                        )
                    else:
                        cells.append(
                            {
                                "date": lesson_date,
                                "record": None,
                                "status": "",
                                "icon": "---",
                                "css": "badge-muted",
                                "label": "Məlumat yoxdur",
                            }
                        )
                rows.append({"student": student, "cells": cells})

        ctx.update(
            {
                "student_groups": StudentGroup.objects.all().order_by("name"),
                "selected_student_group": str(selected_group.pk) if selected_group else group_id,
                "selected_group": selected_group,
                "filter_month": selected_month,
                "prev_month": _month_value(
                    month_year - 1 if month_num == 1 else month_year,
                    12 if month_num == 1 else month_num - 1,
                ),
                "next_month": _month_value(
                    month_year + 1 if month_num == 12 else month_year,
                    1 if month_num == 12 else month_num + 1,
                ),
                "lesson_dates": lesson_dates,
                "attendance_rows": rows,
                "month_stats": month_stats,
                "marked_count": marked_count,
                "expected_count": expected_count,
                "overall_pct": round((attended_count / marked_count * 100), 1)
                if marked_count
                else 0.0,
                "status_choices": ATTENDANCE_MARK_STATUSES,
                "status_options": ATTENDANCE_STATUS_OPTIONS,
            }
        )
        return ctx


class AttendanceQuickMarkView(LoginRequiredMixin, View):
    def post(self, request):
        group_id = (request.POST.get("student_group") or "").strip()
        raw_mark = (request.POST.get("mark") or "").strip()
        fallback_date = date.today()
        month_year, month_num = _parse_month(request.POST.get("month"), fallback_date)
        selected_month = _month_value(month_year, month_num)

        if not group_id.isdigit():
            messages.error(request, "Davamiyyət üçün qrup seçin.")
            return redirect("portal:attendance_list")

        group = get_object_or_404(StudentGroup, pk=int(group_id))

        try:
            student_id_raw, date_raw, status = raw_mark.split("|", 2)
            student_id = int(student_id_raw)
            target_date = date.fromisoformat(date_raw)
        except (TypeError, ValueError):
            messages.error(request, "Yanlış davamiyyət sorğusu.")
            return _attendance_list_redirect(group.pk, selected_month)

        month_year, month_num = _parse_month(request.POST.get("month"), target_date)
        selected_month = _month_value(month_year, month_num)
        allowed_statuses = {value for value, _label in ATTENDANCE_MARK_STATUSES}
        if status not in allowed_statuses:
            messages.error(request, "Yanlış davamiyyət statusu.")
            return _attendance_list_redirect(group.pk, selected_month)

        student = get_object_or_404(
            Student,
            pk=student_id,
            student_group_id=group.pk,
            is_archived=False,
            status=Student.Status.ACTIVE,
        )
        record, created = AttendanceRecord.objects.update_or_create(
            student=student,
            date=target_date,
            defaults={"status": status},
        )
        log_audit(
            request.user,
            "quick_mark",
            "AttendanceRecord",
            str(record.pk),
            {
                "student": student.pk,
                "group": group.pk,
                "date": target_date.isoformat(),
                "status": status,
                "created": created,
            },
        )
        messages.success(
            request,
            f"{student.full_name} — {target_date.isoformat()}: {ATTENDANCE_STATUS_LABELS[status]}.",
        )
        return _attendance_list_redirect(group.pk, selected_month)


class AttendanceMarkView(LoginRequiredMixin, TemplateView):
    template_name = "portal/attendance_form.html"

    def _selection(self):
        source = self.request.POST if self.request.method == "POST" else self.request.GET
        today = date.today()
        target_date = _parse_iso_date(source.get("date"), today)
        month_year, month_num = _parse_month(
            source.get("month"),
            target_date,
        )
        group_id = (source.get("student_group") or "").strip()
        group = None
        if group_id.isdigit():
            group = StudentGroup.objects.filter(pk=int(group_id)).first()
        return group_id, group, target_date, _month_value(month_year, month_num)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        group_id, group, target_date, selected_month = self._selection()
        rows = []
        month_stats = []
        is_lesson_day = True

        if group:
            students = list(
                Student.objects.filter(
                    student_group_id=group.pk,
                    is_archived=False,
                    status=Student.Status.ACTIVE,
                )
                .select_related("student_group")
                .order_by("last_name", "first_name")
            )
            records = {
                record.student_id: record
                for record in AttendanceRecord.objects.filter(
                    student_id__in=[student.pk for student in students],
                    date=target_date,
                )
            }
            for student in students:
                record = records.get(student.pk)
                rows.append(
                    {
                        "student": student,
                        "record": record,
                        "status": record.status if record else AttendanceRecord.Status.PRESENT,
                        "note": record.note if record else "",
                    }
                )

            month_year, month_num = _parse_month(selected_month, target_date)
            for row in (
                AttendanceRecord.objects.filter(
                    student__student_group_id=group.pk,
                    date__year=month_year,
                    date__month=month_num,
                )
                .values("status")
                .annotate(c=Count("id"))
                .order_by("status")
            ):
                row["label"] = ATTENDANCE_STATUS_LABELS.get(row["status"], row["status"])
                month_stats.append(row)
            is_lesson_day = group.is_lesson_day(target_date)

        ctx.update(
            {
                "student_groups": StudentGroup.objects.all().order_by("name"),
                "selected_student_group": str(group.pk) if group else group_id,
                "selected_group": group,
                "filter_date": target_date.isoformat(),
                "filter_month": selected_month,
                "status_choices": ATTENDANCE_MARK_STATUSES,
                "rows": rows,
                "month_stats": month_stats,
                "is_lesson_day": is_lesson_day,
            }
        )
        return ctx

    def post(self, request):
        group_id, group, target_date, selected_month = self._selection()
        if not group:
            messages.error(request, "Davamiyyət üçün qrup seçin.")
            return redirect("portal:attendance_add")

        students = list(
            Student.objects.filter(
                student_group_id=group.pk,
                is_archived=False,
                status=Student.Status.ACTIVE,
            )
            .select_related("student_group")
            .order_by("last_name", "first_name")
        )
        if not students:
            messages.warning(request, f"«{group.name}» qrupunda aktiv tələbə yoxdur.")
            return _attendance_redirect(group.pk, target_date, selected_month)

        if not group.is_lesson_day(target_date):
            messages.warning(
                request,
                "Seçilmiş tarix bu qrup üçün dərs günü deyil; qeyd yenə də saxlandı.",
            )

        allowed_statuses = {value for value, _label in ATTENDANCE_MARK_STATUSES}
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for student in students:
            status = (request.POST.get(f"status_{student.pk}") or "").strip()
            if status not in allowed_statuses:
                skipped_count += 1
                continue
            note = (request.POST.get(f"note_{student.pk}") or "").strip()
            _record, created = AttendanceRecord.objects.update_or_create(
                student=student,
                date=target_date,
                defaults={"status": status, "note": note[:255]},
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        log_audit(
            request.user,
            "bulk_mark",
            "AttendanceRecord",
            str(group.pk),
            {
                "group": group.name,
                "date": target_date.isoformat(),
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
            },
        )
        messages.success(
            request,
            (
                f"«{group.name}» üçün {target_date.isoformat()} davamiyyəti saxlandı: "
                f"{created_count} yeni, {updated_count} yeniləndi."
            ),
        )
        if skipped_count:
            messages.warning(request, f"{skipped_count} tələbə üçün status seçilməyib.")
        return redirect(
            reverse("portal:attendance_list")
            + f"?student_group={group.pk}&month={selected_month}"
        )


class PaymentYearGridView(LoginRequiredMixin, TemplateView):
    template_name = "portal/payment_grid.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        td = date.today()
        raw_y = self.request.GET.get("year", str(td.year))
        try:
            year = int(raw_y)
        except (TypeError, ValueError):
            year = td.year
        students = Student.objects.filter(is_archived=False).select_related(
            "student_group"
        ).order_by("last_name", "first_name")
        pay_qs = MonthlyPayment.objects.filter(year=year).select_related(
            "student"
        )
        pmap = {}
        for p in pay_qs:
            pmap[(p.student_id, p.month)] = p
        rows = []
        for s in students:
            rows.append(
                {
                    "student": s,
                    "cells": [
                        {"month": m, "payment": pmap.get((s.pk, m))}
                        for m in PAYMENT_GRID_MONTH_ORDER
                    ],
                }
            )
        prev_y, next_y = year - 1, year + 1
        ctx.update(
            {
                "grid_year": year,
                "prev_year": prev_y,
                "next_year": next_y,
                "student_rows": rows,
                "months_row": [
                    {"n": n, "label": AZ_MONTH_SHORT[n]}
                    for n in PAYMENT_GRID_MONTH_ORDER
                ],
                "year_total_paid": paid_amount_for_year(year),
            }
        )
        return ctx


class PaymentSetStatusView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            student_id = int(request.POST.get("student_id", ""))
            year = int(request.POST.get("year", ""))
            month = int(request.POST.get("month", ""))
        except (TypeError, ValueError):
            messages.error(request, "Yanlış sorğu.")
            return redirect(reverse("portal:payment_grid") + f"?year={date.today().year}")

        status = request.POST.get("status", "").strip().lower()
        if month < 1 or month > 12 or status not in {
            MonthlyPayment.Status.PAID,
            MonthlyPayment.Status.UNPAID,
            MonthlyPayment.Status.LATE,
        }:
            messages.error(request, "Yanlış ay və ya status.")
            return redirect(reverse("portal:payment_grid") + f"?year={year}")

        student = get_object_or_404(
            Student.objects.select_related("student_group"), pk=student_id
        )
        amount = student.effective_monthly_fee()

        mp, created = MonthlyPayment.objects.get_or_create(
            student=student,
            year=year,
            month=month,
            defaults={
                "amount": amount,
                "status": status,
                "discount": Decimal("0"),
                "remaining_debt": Decimal("0"),
                "payment_method": "",
            },
        )
        mp.amount = amount
        mp.status = status
        if status == MonthlyPayment.Status.PAID:
            mp.payment_date = date.today()
            mp.remaining_debt = Decimal("0")
            if not mp.payment_method:
                mp.payment_method = MonthlyPayment.Method.CASH
        else:
            mp.payment_date = None
            mp.remaining_debt = amount
        if request.user.is_authenticated:
            mp.received_by = request.user
        mp.save()

        action = "create" if created else "update"
        log_audit(
            request.user,
            action,
            "MonthlyPayment",
            str(mp.pk),
            {
                "student": student.pk,
                "year": year,
                "month": month,
                "status": status,
            },
        )

        m_stu, y_stu = student_paid_totals(student.pk, year, month)
        m_all = paid_amount_for_month(year, month)
        y_all = paid_amount_for_year(year)
        name_m = AZ_MONTHS[month] if 1 <= month <= 12 else str(month)

        messages.success(
            request,
            f"{student.full_name} — «{name_m}» statusu yeniləndi. "
            f"Həmin ay üzrə (bu tələbə, ödənib): ₼ {m_stu:.2f}. "
            f"İl üzrə (bu tələbə, ödənib): ₼ {y_stu:.2f}. "
            f"Cədvəldə bütün tələbələr — ay: ₼ {m_all:.2f}, il ({year}, ödənib): ₼ {y_all:.2f}.",
        )
        return redirect(reverse("portal:payment_grid") + f"?year={year}")


class PaymentListView(LoginRequiredMixin, ListView):
    model = MonthlyPayment
    template_name = "portal/payment_list.html"
    context_object_name = "payments"
    paginate_by = 40

    def get_queryset(self):
        qs = MonthlyPayment.objects.select_related("student").all()
        mode = self.request.GET.get("mode", "")
        if mode == "overdue":
            td = date.today()
            qs = qs.filter(
                status__in=[
                    MonthlyPayment.Status.UNPAID,
                    MonthlyPayment.Status.LATE,
                ]
            ).filter(
                Q(year__lt=td.year)
                | Q(year=td.year, month__lt=td.month)
                | Q(status=MonthlyPayment.Status.LATE)
            )
        else:
            y = self.request.GET.get("year")
            m = self.request.GET.get("month")
            if y:
                qs = qs.filter(year=int(y))
            if m:
                qs = qs.filter(month=int(m))
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(student__first_name__icontains=q)
                | Q(student__last_name__icontains=q)
            )
        return qs.order_by("-year", "-month")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        td = date.today()
        y = int(self.request.GET.get("year", td.year))
        m = int(self.request.GET.get("month", td.month))
        rev = MonthlyPayment.objects.filter(
            year=y, month=m, status=MonthlyPayment.Status.PAID
        ).aggregate(t=Sum("amount"))["t"]
        ctx["filter_year"] = y
        ctx["filter_month"] = m
        ctx["month_revenue"] = float(rev) if rev is not None else 0.0
        ctx["mode"] = self.request.GET.get("mode", "")
        return ctx


class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = MonthlyPayment
    form_class = MonthlyPaymentForm
    template_name = "portal/payment_form.html"

    def get_initial(self):
        initial = super().get_initial()
        y = self.request.GET.get("year")
        if y and str(y).isdigit():
            initial["year"] = int(y)
        return initial

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        resp = super().form_valid(form)
        log_audit(
            self.request.user,
            "create",
            "MonthlyPayment",
            str(self.object.pk),
            {"student": self.object.student_id, "month": self.object.month},
        )
        messages.success(self.request, "Ödəniş qeydi əlavə olundu.")
        return resp

    def get_success_url(self):
        return reverse(
            "portal:payment_grid"
        ) + f"?year={self.object.year}"


class PaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = MonthlyPayment
    form_class = MonthlyPaymentForm
    template_name = "portal/payment_form.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        resp = super().form_valid(form)
        log_audit(
            self.request.user,
            "update",
            "MonthlyPayment",
            str(self.object.pk),
            {"student": self.object.student_id},
        )
        messages.success(self.request, "Ödəniş yeniləndi.")
        return resp

    def get_success_url(self):
        return reverse("portal:payment_grid") + f"?year={self.object.year}"


class ExportStudentsXlsxView(LoginRequiredMixin, View):
    def get(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Telebeler"
        ws.append(
            ["ID", "Ad", "Soyad", "Ata adı", "Telefon", "Valideyn", "Qrup mətni", "Qrup", "Aylıq", "Qeydiyyat", "Status", "Arxiv"]
        )
        for s in Student.objects.filter(is_archived=False).select_related("student_group"):
            ws.append(
                [
                    s.id,
                    s.first_name,
                    s.last_name,
                    s.father_name,
                    s.phone,
                    s.parent_phone,
                    s.class_group,
                    s.student_group.name if s.student_group_id else "",
                    float(s.monthly_tuition),
                    s.registration_date.isoformat(),
                    s.get_status_display(),
                    s.is_archived,
                ]
            )
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="students_{timezone.now().date()}.xlsx"'
        )
        wb.save(response)
        return response


class ExportStudentsPdfView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="students_{timezone.now().date()}.pdf"'
        )
        doc = SimpleDocTemplate(response, pagesize=A4)
        data = [["Ad", "Soyad", "Qrup", "Telefon", "Status"]]
        for s in Student.objects.filter(is_archived=False)[:200]:
            data.append(
                [
                    s.first_name,
                    s.last_name,
                    s.class_group,
                    s.phone,
                    s.get_status_display(),
                ]
            )
        t = Table(data, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        doc.build([t])
        return response


class ExportPaymentsXlsxView(LoginRequiredMixin, View):
    def get(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Odenisler"
        ws.append(
            [
                "ID",
                "Telebe",
                "Ay",
                "Il",
                "Mebleg",
                "Odeme tarixi",
                "Status",
                "Endirim",
                "Qaliq",
                "Usul",
            ]
        )
        for p in MonthlyPayment.objects.select_related("student").all()[:5000]:
            ws.append(
                [
                    p.id,
                    p.student.full_name,
                    p.month,
                    p.year,
                    float(p.amount),
                    p.payment_date.isoformat() if p.payment_date else "",
                    p.get_status_display(),
                    float(p.discount),
                    float(p.remaining_debt),
                    p.get_payment_method_display() if p.payment_method else "",
                ]
            )
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="payments_{timezone.now().date()}.xlsx"'
        )
        wb.save(response)
        return response

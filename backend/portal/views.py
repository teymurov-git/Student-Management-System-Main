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


def _parse_attendance_date(raw):
    try:
        return date.fromisoformat((raw or "").strip())
    except (TypeError, ValueError):
        return date.today()


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


class StudentGroupCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = StudentGroupQuickForm(request.POST)
        if form.is_valid():
            g = form.save()
            log_audit(request.user, "create", "StudentGroup", str(g.pk), {"name": g.name})
            messages.success(request, f"Qrup «{g.name}» əlavə olundu.")
        else:
            for err in form.errors.values():
                for e in err:
                    messages.error(request, str(e))
        next_url = (request.POST.get("next") or "").strip()
        if next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect("portal:student_list")


class StudentGroupDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        group = get_object_or_404(StudentGroup, pk=pk)
        name = group.name
        gid = group.pk
        student_count = Student.objects.filter(student_group_id=gid).count()
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
        next_url = (request.POST.get("next") or "").strip()
        if next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect("portal:student_list")


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


class AttendanceListView(LoginRequiredMixin, ListView):
    model = AttendanceRecord
    template_name = "portal/attendance_list.html"
    context_object_name = "records"
    paginate_by = 50

    def get_queryset(self):
        qs = AttendanceRecord.objects.select_related(
            "student", "student__student_group"
        ).all()

        raw_date = self.request.GET.get("date", "").strip()
        if raw_date:
            qs = qs.filter(date=_parse_attendance_date(raw_date))

        gid = self.request.GET.get("student_group", "").strip()
        if gid.isdigit():
            qs = qs.filter(student__student_group_id=int(gid))

        class_group = self.request.GET.get("class_group", "").strip()
        if class_group:
            qs = qs.filter(student__class_group=class_group)

        return qs.order_by("-date", "student__last_name", "student__first_name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        total = qs.count()
        attended = qs.filter(
            status__in=[AttendanceRecord.Status.PRESENT, AttendanceRecord.Status.LATE]
        ).count()
        labels = dict(AttendanceRecord.Status.choices)
        gid = self.request.GET.get("student_group", "").strip()
        filter_date = self.request.GET.get("date", "").strip()
        stat_date = _parse_attendance_date(filter_date)
        stats_qs = AttendanceRecord.objects.filter(
            date__year=stat_date.year,
            date__month=stat_date.month,
        )
        if gid.isdigit():
            stats_qs = stats_qs.filter(student__student_group_id=int(gid))
        class_group = self.request.GET.get("class_group", "").strip()
        if class_group:
            stats_qs = stats_qs.filter(student__class_group=class_group)

        ctx.update(
            {
                "overall_pct": round((attended / total * 100), 1) if total else 0.0,
                "filter_date": filter_date,
                "filter_class": class_group,
                "student_groups": StudentGroup.objects.all().order_by("name"),
                "selected_student_group": gid,
                "month_stats": [
                    {"status": labels.get(row["status"], row["status"]), "c": row["c"]}
                    for row in stats_qs.values("status")
                    .annotate(c=Count("id"))
                    .order_by("status")
                ],
            }
        )
        return ctx


class AttendanceGroupCreateView(LoginRequiredMixin, View):
    template_name = "portal/attendance_form.html"

    def _build_context(self, request, errors=None):
        gid = (request.POST.get("student_group") or request.GET.get("student_group") or "").strip()
        attendance_date = _parse_attendance_date(
            request.POST.get("date") or request.GET.get("date")
        )
        group = StudentGroup.objects.filter(pk=int(gid)).first() if gid.isdigit() else None
        rows = []
        if group:
            students = group.students.filter(
                is_archived=False, status=Student.Status.ACTIVE
            ).order_by("last_name", "first_name")
            records = {
                record.student_id: record
                for record in AttendanceRecord.objects.filter(
                    student__student_group_id=group.pk, date=attendance_date
                )
            }
            for student in students:
                record = records.get(student.pk)
                rows.append(
                    {
                        "student": student,
                        "status": record.status if record else AttendanceRecord.Status.PRESENT,
                        "note": record.note if record else "",
                    }
                )

        return {
            "errors": errors or [],
            "student_groups": StudentGroup.objects.all().order_by("name"),
            "selected_student_group": str(group.pk) if group else gid,
            "selected_group": group,
            "attendance_date": attendance_date.isoformat(),
            "status_choices": AttendanceRecord.Status.choices,
            "rows": rows,
        }

    def get(self, request):
        return self.render_to_response(request)

    def post(self, request):
        gid = request.POST.get("student_group", "").strip()
        if not gid.isdigit():
            return self.render_to_response(request, ["Qrup seçilməlidir."])

        group = get_object_or_404(StudentGroup, pk=int(gid))
        attendance_date = _parse_attendance_date(request.POST.get("date"))
        allowed_statuses = {value for value, _label in AttendanceRecord.Status.choices}
        students = group.students.filter(
            is_archived=False, status=Student.Status.ACTIVE
        ).order_by("last_name", "first_name")
        updated = 0

        for student in students:
            status = request.POST.get(
                f"status_{student.pk}", AttendanceRecord.Status.PRESENT
            )
            if status not in allowed_statuses:
                return self.render_to_response(request, ["Yanlış davamiyyət statusu."])
            note = request.POST.get(f"note_{student.pk}", "").strip()
            AttendanceRecord.objects.update_or_create(
                student=student,
                date=attendance_date,
                defaults={"status": status, "note": note},
            )
            updated += 1

        log_audit(
            request.user,
            "bulk_upsert",
            "AttendanceRecord",
            "",
            {"group": group.name, "date": attendance_date.isoformat(), "count": updated},
        )
        messages.success(
            request,
            f"«{group.name}» qrupu üçün {attendance_date.isoformat()} tarixli {updated} davamiyyət qeydi saxlanıldı.",
        )
        return redirect(
            reverse("portal:attendance_list")
            + f"?student_group={group.pk}&date={attendance_date.isoformat()}"
        )

    def render_to_response(self, request, errors=None):
        from django.shortcuts import render

        return render(request, self.template_name, self._build_context(request, errors))


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

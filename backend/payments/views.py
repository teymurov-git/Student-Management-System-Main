from datetime import date

from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from audit.utils import log_audit

from .models import MonthlyPayment
from .serializers import MonthlyPaymentSerializer, MonthlyPaymentWriteSerializer


class MonthlyPaymentViewSet(viewsets.ModelViewSet):
    queryset = MonthlyPayment.objects.select_related("student", "received_by").all()
    filterset_fields = ("student", "month", "year", "status")
    search_fields = ("student__first_name", "student__last_name", "notes")
    ordering_fields = ("year", "month", "payment_date", "amount")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MonthlyPaymentWriteSerializer
        return MonthlyPaymentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(student__first_name__icontains=q)
                | Q(student__last_name__icontains=q)
                | Q(notes__icontains=q)
            )
        return qs

    def perform_create(self, serializer):
        obj = serializer.save()
        log_audit(
            self.request.user, "create", "MonthlyPayment", str(obj.pk), serializer.data
        )

    def perform_update(self, serializer):
        obj = serializer.save()
        log_audit(
            self.request.user, "update", "MonthlyPayment", str(obj.pk), serializer.data
        )

    def perform_destroy(self, instance):
        pk = str(instance.pk)
        instance.delete()
        log_audit(self.request.user, "delete", "MonthlyPayment", pk, {})

    @action(detail=False, methods=["get"])
    def debtors(self, request):
        qs = (
            self.get_queryset()
            .filter(
                Q(remaining_debt__gt=0)
                | Q(
                    status__in=[
                        MonthlyPayment.Status.UNPAID,
                        MonthlyPayment.Status.LATE,
                    ]
                )
            )
            .order_by("-year", "-month")
        )
        page = self.paginate_queryset(qs)
        ser = MonthlyPaymentSerializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        today_d = date.today()
        qs = self.get_queryset().filter(
            status__in=[
                MonthlyPayment.Status.UNPAID,
                MonthlyPayment.Status.LATE,
            ],
        )
        qs = qs.filter(
            Q(year__lt=today_d.year)
            | Q(year=today_d.year, month__lt=today_d.month)
            | Q(status=MonthlyPayment.Status.LATE)
        ).order_by("-year", "-month")
        return Response(MonthlyPaymentSerializer(qs[:500], many=True).data)

    @action(detail=False, methods=["get"])
    def monthly_revenue(self, request):
        td = date.today()
        y = int(request.query_params.get("year", td.year))
        m = int(request.query_params.get("month", td.month))
        agg = self.get_queryset().filter(
            year=y, month=m, status=MonthlyPayment.Status.PAID
        ).aggregate(total=Sum("amount"))
        return Response({"year": y, "month": m, "total_paid": agg["total"] or 0})

    @action(detail=False, methods=["get"])
    def export_excel(self, request):
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
                "Qeyd",
            ]
        )
        for p in self.get_queryset()[:5000]:
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
                    p.notes,
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

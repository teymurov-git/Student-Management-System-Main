from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from audit.utils import log_audit
from attendance.models import AttendanceRecord
from attendance.serializers import AttendanceRecordSerializer
from exams.models import ExamResult
from exams.serializers import ExamResultSerializer
from payments.models import MonthlyPayment
from payments.serializers import MonthlyPaymentSerializer

from .models import Student
from .serializers import StudentSerializer


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    search_fields = (
        "first_name",
        "last_name",
        "father_name",
        "phone",
        "parent_phone",
        "class_group",
        "notes",
    )
    ordering_fields = ("created_at", "registration_date", "last_name")
    filterset_fields = ("class_group", "student_group", "status", "is_archived")

    def get_queryset(self):
        qs = super().get_queryset()
        if (
            self.action == "list"
            and self.request.query_params.get("archived") != "1"
        ):
            qs = qs.filter(is_archived=False)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(phone__icontains=q)
                | Q(class_group__icontains=q)
            )
        return qs

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        student = self.get_object()
        student.is_archived = True
        student.save(update_fields=["is_archived", "updated_at"])
        log_audit(request.user, "update", "Student", str(student.pk), {"is_archived": True})
        return Response(StudentSerializer(student).data)

    def perform_create(self, serializer):
        obj = serializer.save()
        log_audit(self.request.user, "create", "Student", str(obj.pk), serializer.data)

    def perform_update(self, serializer):
        obj = serializer.save()
        log_audit(self.request.user, "update", "Student", str(obj.pk), serializer.data)

    def perform_destroy(self, instance):
        pk = str(instance.pk)
        instance.delete()
        log_audit(self.request.user, "delete", "Student", pk, {})

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        student = self.get_object()
        payments = MonthlyPayment.objects.filter(student=student).order_by(
            "-year", "-month"
        )
        attendance = AttendanceRecord.objects.filter(student=student).order_by("-date")
        exams = ExamResult.objects.filter(student=student).order_by("-year", "-month")
        return Response(
            {
                "student": StudentSerializer(student).data,
                "payments": MonthlyPaymentSerializer(payments, many=True).data,
                "attendance": AttendanceRecordSerializer(attendance, many=True).data,
                "exams": ExamResultSerializer(exams, many=True).data,
            }
        )

    @action(detail=False, methods=["get"])
    def export_excel(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Telebeler"
        headers = [
            "ID",
            "Ad",
            "Soyad",
            "Ata adı",
            "Telefon",
            "Valideyn",
            "Qrup",
            "Qeydiyyat",
            "Status",
            "Arxiv",
        ]
        ws.append(headers)
        for s in Student.objects.filter(is_archived=False):
            ws.append(
                [
                    s.id,
                    s.first_name,
                    s.last_name,
                    s.father_name,
                    s.phone,
                    s.parent_phone,
                    s.class_group,
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

    @action(detail=False, methods=["get"])
    def export_pdf(self, request):
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
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        doc.build([t])
        return response

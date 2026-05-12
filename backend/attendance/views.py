from calendar import monthrange
from datetime import date

from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from audit.utils import log_audit

from .models import AttendanceRecord
from .serializers import AttendanceRecordSerializer


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.select_related(
        "student", "student__student_group"
    ).all()
    serializer_class = AttendanceRecordSerializer
    filterset_fields = ("student", "date", "status")
    search_fields = ("student__first_name", "student__last_name", "note")
    ordering_fields = ("date", "created_at")

    def get_queryset(self):
        qs = super().get_queryset()
        df = self.request.query_params.get("date_from")
        dt = self.request.query_params.get("date_to")
        cg = self.request.query_params.get("class_group")
        gid = self.request.query_params.get("student_group")
        if df:
            qs = qs.filter(date__gte=df)
        if dt:
            qs = qs.filter(date__lte=dt)
        if cg:
            qs = qs.filter(student__class_group=cg)
        if gid and str(gid).isdigit():
            qs = qs.filter(student__student_group_id=int(gid))
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(student__first_name__icontains=q)
                | Q(student__last_name__icontains=q)
            )
        return qs

    def perform_create(self, serializer):
        obj = serializer.save()
        log_audit(
            self.request.user,
            "create",
            "AttendanceRecord",
            str(obj.pk),
            serializer.data,
        )

    def perform_update(self, serializer):
        obj = serializer.save()
        log_audit(
            self.request.user,
            "update",
            "AttendanceRecord",
            str(obj.pk),
            serializer.data,
        )

    def perform_destroy(self, instance):
        pk = str(instance.pk)
        instance.delete()
        log_audit(self.request.user, "delete", "AttendanceRecord", pk, {})

    @action(detail=False, methods=["get"])
    def summary_student(self, request):
        student_id = request.query_params.get("student")
        if not student_id:
            return Response({"detail": "student param tələb olunur"}, status=400)
        qs = self.get_queryset().filter(student_id=student_id)
        total = qs.count()
        present = qs.filter(status=AttendanceRecord.Status.PRESENT).count()
        pct = round((present / total * 100), 1) if total else 0.0
        return Response({"total_sessions": total, "present": present, "percent": pct})

    @action(detail=False, methods=["get"])
    def summary_month(self, request):
        y = int(request.query_params.get("year", date.today().year))
        m = int(request.query_params.get("month", date.today().month))
        start = date(y, m, 1)
        last = monthrange(y, m)[1]
        end = date(y, m, last)
        qs = self.get_queryset().filter(date__gte=start, date__lte=end)
        by_status = qs.values("status").annotate(c=Count("id"))
        return Response(
            {
                "year": y,
                "month": m,
                "by_status": {row["status"]: row["c"] for row in by_status},
                "total_rows": qs.count(),
            }
        )

    @action(detail=False, methods=["get"])
    def overall_percent(self, request):
        qs = self.get_queryset()
        total = qs.count()
        present = qs.filter(status=AttendanceRecord.Status.PRESENT).count()
        late = qs.filter(status=AttendanceRecord.Status.LATE).count()
        # İştirak + gecikənlər dərsə gəlib sayıla bilər
        attended = present + late
        pct = round((attended / total * 100), 1) if total else 0.0
        return Response(
            {
                "total_records": total,
                "attended_count": attended,
                "attendance_percent": pct,
            }
        )

    @action(detail=False, methods=["get"])
    def today_present(self, request):
        d = request.query_params.get("date") or date.today().isoformat()
        qs = self.get_queryset().filter(
            date=d,
            status__in=[
                AttendanceRecord.Status.PRESENT,
                AttendanceRecord.Status.LATE,
            ],
        )
        return Response({"date": d, "count": qs.count()})

    @action(detail=False, methods=["get"])
    def export_excel(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Davamiyyet"
        ws.append(["ID", "Telebe ID", "Ad Soyad", "Tarix", "Status", "Qeyd"])
        for r in self.get_queryset()[:8000]:
            ws.append(
                [
                    r.id,
                    r.student_id,
                    r.student.full_name,
                    r.date.isoformat(),
                    r.get_status_display(),
                    r.note,
                ]
            )
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="attendance_{timezone.now().date()}.xlsx"'
        )
        wb.save(response)
        return response

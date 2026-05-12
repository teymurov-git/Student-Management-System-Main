from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from audit.utils import log_audit

from .models import ExamResult
from .serializers import ExamResultSerializer


class ExamResultViewSet(viewsets.ModelViewSet):
    queryset = ExamResult.objects.select_related("student").all()
    serializer_class = ExamResultSerializer
    filterset_fields = ("student", "month", "year")
    search_fields = ("name", "teacher_notes", "student__first_name", "student__last_name")
    ordering_fields = ("year", "month", "percentage", "total_score")

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(student__first_name__icontains=q)
                | Q(student__last_name__icontains=q)
                | Q(name__icontains=q)
            )
        return qs

    def perform_create(self, serializer):
        obj = serializer.save()
        log_audit(self.request.user, "create", "ExamResult", str(obj.pk), serializer.data)

    def perform_update(self, serializer):
        obj = serializer.save()
        log_audit(self.request.user, "update", "ExamResult", str(obj.pk), serializer.data)

    def perform_destroy(self, instance):
        pk = str(instance.pk)
        instance.delete()
        log_audit(self.request.user, "delete", "ExamResult", pk, {})

    @action(detail=False, methods=["get"])
    def chart_student(self, request):
        sid = request.query_params.get("student")
        if not sid:
            return Response({"detail": "student tələb olunur"}, status=400)
        rows = (
            self.get_queryset()
            .filter(student_id=sid)
            .order_by("year", "month")
            .values("month", "year", "percentage")
        )
        return Response(list(rows))

    @action(detail=False, methods=["get"])
    def best(self, request):
        sid = request.query_params.get("student")
        qs = self.get_queryset()
        if sid:
            qs = qs.filter(student_id=sid)
        row = qs.order_by("-percentage").first()
        if not row:
            return Response(None)
        return Response(ExamResultSerializer(row).data)

    @action(detail=False, methods=["get"])
    def weak_topics(self, request):
        """Ən aşağı orta balı olan fənlər (bütün nəticələr üzrə)."""
        sid = request.query_params.get("student")
        qs = self.get_queryset()
        if sid:
            qs = qs.filter(student_id=sid)
        totals = {}
        counts = {}
        for ex in qs[:500]:
            if not isinstance(ex.subject_scores, dict):
                continue
            for sub, val in ex.subject_scores.items():
                try:
                    v = float(val)
                except (TypeError, ValueError):
                    continue
                totals[sub] = totals.get(sub, 0) + v
                counts[sub] = counts.get(sub, 0) + 1
        avgs = []
        for sub in totals:
            c = counts[sub] or 1
            avgs.append({"subject": sub, "avg": round(totals[sub] / c, 2)})
        avgs.sort(key=lambda x: x["avg"])
        return Response({"weakest": avgs[:8]})

    @action(detail=False, methods=["get"])
    def export_excel(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Sinavlar"
        ws.append(
            [
                "ID",
                "Telebe",
                "Ad",
                "Ay",
                "Il",
                "Faiz",
                "Umumi bal",
                "Fennler JSON",
                "Qeyd",
            ]
        )
        for e in self.get_queryset()[:5000]:
            ws.append(
                [
                    e.id,
                    e.student_id,
                    e.student.full_name,
                    e.month,
                    e.year,
                    float(e.percentage),
                    float(e.total_score),
                    str(e.subject_scores),
                    e.teacher_notes,
                ]
            )
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="exams_{timezone.now().date()}.xlsx"'
        )
        wb.save(response)
        return response

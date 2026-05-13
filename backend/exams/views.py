from decimal import Decimal

from django.db.models import F, Q
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from audit.utils import log_audit
from students.models import Student

from .models import ExamResult, MonthlyExam, MonthlyExamScore
from .serializers import (
    ExamResultSerializer,
    MonthlyExamScoreSerializer,
    MonthlyExamSerializer,
)


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


class MonthlyExamViewSet(viewsets.ModelViewSet):
    queryset = MonthlyExam.objects.select_related("student_group").all()
    serializer_class = MonthlyExamSerializer
    filterset_fields = ("student_group",)
    search_fields = ("title",)
    ordering_fields = ("sort_order", "id", "created_at")
    ordering = ("sort_order", "id")

    def perform_create(self, serializer):
        obj = serializer.save()
        log_audit(self.request.user, "create", "MonthlyExam", str(obj.pk), serializer.data)

    def perform_update(self, serializer):
        obj = serializer.save()
        log_audit(self.request.user, "update", "MonthlyExam", str(obj.pk), serializer.data)

    def perform_destroy(self, instance):
        pk = str(instance.pk)
        instance.delete()
        log_audit(self.request.user, "delete", "MonthlyExam", pk, {})

    @action(detail=False, methods=["get"])
    def grid(self, request):
        """Qrup üçün sütunlar, tələbələr, xanalar və dinamik orta faiz (yalnız daxil edilmiş sınaqlar)."""
        raw_gid = (request.query_params.get("student_group") or "").strip()
        if not raw_gid.isdigit():
            return Response({"detail": "student_group parametri tələb olunur"}, status=400)
        group_id = int(raw_gid)
        exams = list(
            MonthlyExam.objects.filter(student_group_id=group_id).order_by("sort_order", "id")
        )
        exam_ids = [e.pk for e in exams]
        students = list(
            Student.objects.filter(
                student_group_id=group_id,
                is_archived=False,
                academic_year_start=F("student_group__academic_year_start"),
            )
            .select_related("student_group")
            .order_by("last_name", "first_name")
        )
        score_rows = MonthlyExamScore.objects.filter(monthly_exam_id__in=exam_ids).values(
            "student_id", "monthly_exam_id", "score_percent"
        )
        scores = {}
        for r in score_rows:
            sid = r["student_id"]
            scores.setdefault(sid, {})[r["monthly_exam_id"]] = str(r["score_percent"])

        averages = {}
        for s in students:
            vals = []
            for eid in exam_ids:
                cell = scores.get(s.pk, {}).get(eid)
                if cell is not None:
                    vals.append(Decimal(cell))
            if vals:
                total = sum(vals, start=Decimal("0"))
                averages[s.pk] = str((total / len(vals)).quantize(Decimal("0.01")))
            else:
                averages[s.pk] = None

        return Response(
            {
                "student_group": group_id,
                "exams": MonthlyExamSerializer(exams, many=True).data,
                "students": [
                    {"id": s.pk, "full_name": s.full_name, "average_percent": averages.get(s.pk)}
                    for s in students
                ],
                "scores": scores,
            }
        )


class MonthlyExamScoreViewSet(viewsets.ModelViewSet):
    queryset = MonthlyExamScore.objects.select_related(
        "monthly_exam", "monthly_exam__student_group", "student"
    ).all()
    serializer_class = MonthlyExamScoreSerializer
    filterset_fields = ("monthly_exam", "student")
    ordering = ("-updated_at",)

    def perform_create(self, serializer):
        obj = serializer.save()
        log_audit(self.request.user, "create", "MonthlyExamScore", str(obj.pk), serializer.data)

    def perform_update(self, serializer):
        obj = serializer.save()
        log_audit(self.request.user, "update", "MonthlyExamScore", str(obj.pk), serializer.data)

    def perform_destroy(self, instance):
        pk = str(instance.pk)
        instance.delete()
        log_audit(self.request.user, "delete", "MonthlyExamScore", pk, {})

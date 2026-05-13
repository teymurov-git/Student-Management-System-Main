from decimal import Decimal

from rest_framework import serializers

from .models import ExamResult, MonthlyExam, MonthlyExamScore


class ExamResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = ExamResult
        fields = (
            "id",
            "student",
            "student_name",
            "name",
            "month",
            "year",
            "subject_scores",
            "total_score",
            "max_total",
            "percentage",
            "teacher_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        scores = attrs.get("subject_scores")
        if scores is None and getattr(self, "instance", None):
            scores = self.instance.subject_scores
        scores = scores or {}
        if isinstance(scores, dict) and scores:
            total = sum(Decimal(str(v)) for v in scores.values())
            attrs["total_score"] = total
            mx = attrs.get("max_total")
            if mx is None and getattr(self, "instance", None):
                mx = self.instance.max_total
            mx = mx or Decimal("100")
            if mx > 0:
                attrs["percentage"] = (total / mx * Decimal("100")).quantize(
                    Decimal("0.01")
                )
        return attrs


class MonthlyExamSerializer(serializers.ModelSerializer):
    student_group_name = serializers.CharField(source="student_group.name", read_only=True)
    scores_entered_count = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyExam
        fields = (
            "id",
            "student_group",
            "student_group_name",
            "title",
            "sort_order",
            "scores_entered_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_scores_entered_count(self, obj):
        return obj.scores.count()


class MonthlyExamScoreSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = MonthlyExamScore
        fields = (
            "id",
            "monthly_exam",
            "student",
            "student_name",
            "score_percent",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        exam = attrs.get("monthly_exam")
        student = attrs.get("student")
        if self.instance:
            exam = exam or self.instance.monthly_exam
            student = student or self.instance.student
        if exam and student:
            if student.student_group_id != exam.student_group_id:
                raise serializers.ValidationError(
                    {"student": "Tələbə bu sınağın qrupuna aid deyil."},
                )
            if student.academic_year_start != exam.student_group.academic_year_start:
                raise serializers.ValidationError(
                    {"student": "Tələbənin tədris ili qrupun ili ilə uyğun olmalıdır."},
                )
        sp = attrs.get("score_percent")
        if sp is not None and (sp < Decimal("0") or sp > Decimal("100")):
            raise serializers.ValidationError(
                {"score_percent": "Faiz 0 ilə 100 arasında olmalıdır."},
            )
        return attrs

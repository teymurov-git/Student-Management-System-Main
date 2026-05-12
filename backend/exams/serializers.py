from decimal import Decimal

from rest_framework import serializers

from .models import ExamResult


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

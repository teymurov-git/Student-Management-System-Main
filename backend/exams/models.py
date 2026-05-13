from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class ExamResult(models.Model):
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="exam_results",
    )
    name = models.CharField("Sınağın adı", max_length=200, default="Aylıq sınaq")
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    subject_scores = models.JSONField(
        default=dict,
        help_text='Məs: {"Riyaziyyat": 18, "Azərbaycan dili": 15}',
    )
    total_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_total = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    teacher_notes = models.TextField("Müəllim qeydi", blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-month"]
        indexes = [
            models.Index(fields=["student", "year", "month"]),
        ]

    def __str__(self):
        return f"{self.student_id} {self.year}-{self.month:02d} {self.percentage}%"


class MonthlyExam(models.Model):
    """Qrup üçün aylıq sınaq sütunu (faiz daxil edilməsi üçün)."""

    student_group = models.ForeignKey(
        "students.StudentGroup",
        on_delete=models.CASCADE,
        related_name="monthly_exams",
        verbose_name="Qrup",
    )
    title = models.CharField("Sınağın adı", max_length=120)
    sort_order = models.PositiveSmallIntegerField("Sıra", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["student_group", "sort_order"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.student_group_id})"


class MonthlyExamScore(models.Model):
    """Daxil edilmiş faiz — yalnız mövcud sətirlər orta hesablamaya daxil edilir."""

    monthly_exam = models.ForeignKey(
        MonthlyExam,
        on_delete=models.CASCADE,
        related_name="scores",
        verbose_name="Aylıq sınaq",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="monthly_exam_scores",
        verbose_name="Tələbə",
    )
    score_percent = models.DecimalField("Faiz (%)", max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["monthly_exam", "student"],
                name="exams_monthlyexamscore_exam_student_uniq",
            ),
        ]

    def clean(self):
        super().clean()
        if not self.student_id or not self.monthly_exam_id:
            return
        group_id = self.monthly_exam.student_group_id
        if self.student.student_group_id != group_id:
            raise ValidationError(
                {"student": "Tələbə bu sınağın qrupuna aid deyil."},
            )
        if self.student.academic_year_start != self.monthly_exam.student_group.academic_year_start:
            raise ValidationError(
                {"student": "Tələbənin tədris ili qrupun ili ilə uyğun olmalıdır."},
            )
        if self.score_percent is not None:
            if self.score_percent < Decimal("0") or self.score_percent > Decimal("100"):
                raise ValidationError(
                    {"score_percent": "Faiz 0 ilə 100 arasında olmalıdır."},
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

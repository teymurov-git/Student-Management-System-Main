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

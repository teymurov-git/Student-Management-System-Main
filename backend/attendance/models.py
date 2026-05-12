from django.db import models


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "İştirak edib"
        ABSENT = "absent", "Gəlməyib"
        LATE = "late", "Gecikib"
        EXCUSED = "excused", "İcazəli"

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    date = models.DateField()
    status = models.CharField(max_length=16, choices=Status.choices)
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "student_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "date"],
                name="uniq_student_attendance_date",
            )
        ]
        indexes = [models.Index(fields=["date", "status"])]

    def __str__(self):
        return f"{self.student_id} {self.date} {self.status}"

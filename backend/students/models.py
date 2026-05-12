from datetime import date, datetime
from decimal import Decimal

from django.db import models


class StudentGroup(models.Model):
    LESSON_WEEKDAY_CHOICES = (
        ("0", "Bazar ertəsi"),
        ("1", "Çərşənbə axşamı"),
        ("2", "Çərşənbə"),
        ("3", "Cümə axşamı"),
        ("4", "Cümə"),
        ("5", "Şənbə"),
        ("6", "Bazar"),
    )
    LESSON_WEEKDAY_LABELS = dict(LESSON_WEEKDAY_CHOICES)

    name = models.CharField("Qrupun adı", max_length=80, unique=True)
    monthly_fee = models.DecimalField("Aylıq ödəniş (₼)", max_digits=12, decimal_places=2, default=0)
    lesson_weekdays = models.CharField(
        "Dərs günləri",
        max_length=32,
        blank=True,
        default="",
        help_text="Həftənin dərs keçirilən günləri.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def normalize_lesson_weekdays(cls, weekdays) -> str:
        if not weekdays:
            return ""

        values = weekdays.split(",") if isinstance(weekdays, str) else weekdays
        valid_values = {value for value, _label in cls.LESSON_WEEKDAY_CHOICES}
        normalized = []

        for value in values:
            value = str(value).strip()
            if value in valid_values and value not in normalized:
                normalized.append(value)

        return ",".join(sorted(normalized, key=int))

    @property
    def lesson_weekday_numbers(self) -> tuple[int, ...]:
        normalized = self.normalize_lesson_weekdays(self.lesson_weekdays)
        if not normalized:
            return ()
        return tuple(int(value) for value in normalized.split(","))

    @property
    def lesson_weekday_labels(self) -> tuple[str, ...]:
        return tuple(
            self.LESSON_WEEKDAY_LABELS[str(value)]
            for value in self.lesson_weekday_numbers
        )

    @property
    def lesson_weekday_label_text(self) -> str:
        return ", ".join(self.lesson_weekday_labels)

    def is_lesson_day(self, target_date: date | datetime) -> bool:
        if isinstance(target_date, datetime):
            target_date = target_date.date()
        days = self.lesson_weekday_numbers
        if not days:
            return True
        return target_date.weekday() in days

    def clean(self):
        super().clean()
        self.lesson_weekdays = self.normalize_lesson_weekdays(self.lesson_weekdays)

    def save(self, *args, **kwargs):
        self.lesson_weekdays = self.normalize_lesson_weekdays(self.lesson_weekdays)
        super().save(*args, **kwargs)


class Student(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        INACTIVE = "inactive", "Passiv"

    first_name = models.CharField("Ad", max_length=120)
    last_name = models.CharField("Soyad", max_length=120)
    father_name = models.CharField("Ata adı", max_length=120, blank=True)
    phone = models.CharField("Telefon", max_length=32)
    parent_phone = models.CharField(
        "Valideyn telefonu", max_length=32, blank=True, default=""
    )
    student_group = models.ForeignKey(
        StudentGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
        verbose_name="Qrup",
    )
    monthly_tuition = models.DecimalField(
        "Fərdi aylıq ödəniş (₼)",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="0 olsa, seçilmiş qrupun aylığı tətbiq olunur.",
    )
    class_group = models.CharField("Qrup (sinxron)", max_length=64, blank=True, default="")
    registration_date = models.DateField("Qeydiyyat tarixi")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    notes = models.TextField("Qeyd", blank=True, default="")
    is_archived = models.BooleanField("Arxiv", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["class_group"]),
            models.Index(fields=["is_archived", "status"]),
            models.Index(fields=["student_group"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def effective_monthly_fee(self) -> Decimal:
        if self.monthly_tuition and self.monthly_tuition > 0:
            return self.monthly_tuition
        if self.student_group_id:
            return self.student_group.monthly_fee
        return Decimal("0")

    def save(self, *args, **kwargs):
        if self.student_group_id:
            self.class_group = self.student_group.name
        super().save(*args, **kwargs)

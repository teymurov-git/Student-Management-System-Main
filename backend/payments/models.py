from django.conf import settings
from django.db import models


class MonthlyPayment(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Ödənib"
        UNPAID = "unpaid", "Ödənməyib"
        LATE = "late", "Gecikib"

    class Method(models.TextChoices):
        CASH = "cash", "Nağd"
        CARD = "card", "Kart"
        TRANSFER = "transfer", "Köçürmə"

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.UNPAID
    )
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remaining_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=16,
        choices=Method.choices,
        blank=True,
        default="",
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments_received",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "month", "year"],
                name="uniq_student_month_year_payment",
            )
        ]
        indexes = [
            models.Index(fields=["year", "month", "status"]),
        ]

    def __str__(self):
        return f"{self.student_id} {self.year}-{self.month:02d}"

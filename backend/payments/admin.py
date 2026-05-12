from django.contrib import admin

from .models import MonthlyPayment


@admin.register(MonthlyPayment)
class MonthlyPaymentAdmin(admin.ModelAdmin):
    list_display = ("student", "year", "month", "amount", "status", "payment_date")
    list_filter = ("year", "month", "status")
    search_fields = ("student__first_name", "student__last_name")

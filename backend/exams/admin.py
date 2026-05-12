from django.contrib import admin

from .models import ExamResult


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ("student", "year", "month", "percentage", "name")
    list_filter = ("year", "month")

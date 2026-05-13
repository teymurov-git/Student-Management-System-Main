from django.contrib import admin

from .models import ExamResult, MonthlyExam, MonthlyExamScore


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ("student", "year", "month", "percentage", "name")
    list_filter = ("year", "month")


@admin.register(MonthlyExam)
class MonthlyExamAdmin(admin.ModelAdmin):
    list_display = ("title", "student_group", "sort_order", "updated_at")
    list_filter = ("student_group",)


@admin.register(MonthlyExamScore)
class MonthlyExamScoreAdmin(admin.ModelAdmin):
    list_display = ("student", "monthly_exam", "score_percent", "updated_at")
    list_filter = ("monthly_exam",)

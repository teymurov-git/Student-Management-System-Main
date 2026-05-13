from django.contrib import admin

from .models import Student, StudentGroup


@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "academic_year_start", "monthly_fee", "lesson_days")
    search_fields = ("name",)
    list_filter = ("academic_year_start",)

    def lesson_days(self, obj):
        return obj.lesson_weekday_label_text or "Bütün günlər"

    lesson_days.short_description = "Dərs günləri"


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "last_name",
        "first_name",
        "academic_year_start",
        "student_group",
        "class_group",
        "monthly_tuition",
        "status",
        "is_archived",
        "registration_date",
    )
    list_filter = ("status", "is_archived", "student_group", "academic_year_start")
    search_fields = ("first_name", "last_name", "phone", "class_group")

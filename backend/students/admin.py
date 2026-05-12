from django.contrib import admin

from .models import Student, StudentGroup


@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "monthly_fee")
    search_fields = ("name",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "last_name",
        "first_name",
        "student_group",
        "class_group",
        "monthly_tuition",
        "status",
        "is_archived",
        "registration_date",
    )
    list_filter = ("status", "is_archived", "student_group")
    search_fields = ("first_name", "last_name", "phone", "class_group")

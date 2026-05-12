from django.contrib import admin

from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "status")
    list_filter = ("status", "date")

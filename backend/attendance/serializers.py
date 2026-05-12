from rest_framework import serializers

from .models import AttendanceRecord


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = (
            "id",
            "student",
            "student_name",
            "date",
            "status",
            "note",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

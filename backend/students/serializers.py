from rest_framework import serializers

from .models import Student, StudentGroup


class StudentGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentGroup
        fields = ("id", "name", "monthly_fee")


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Student
        fields = (
            "id",
            "first_name",
            "last_name",
            "father_name",
            "phone",
            "parent_phone",
            "student_group",
            "monthly_tuition",
            "class_group",
            "registration_date",
            "status",
            "notes",
            "is_archived",
            "full_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "full_name")

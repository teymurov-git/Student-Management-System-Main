from rest_framework import serializers

from .models import Student, StudentGroup


class StudentGroupSerializer(serializers.ModelSerializer):
    lesson_weekday_numbers = serializers.ListField(
        child=serializers.IntegerField(),
        read_only=True,
    )
    lesson_weekday_labels = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )

    class Meta:
        model = StudentGroup
        fields = (
            "id",
            "name",
            "monthly_fee",
            "lesson_weekdays",
            "lesson_weekday_numbers",
            "lesson_weekday_labels",
        )


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

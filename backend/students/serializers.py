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
            "academic_year_start",
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
            "academic_year_start",
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
        extra_kwargs = {
            "academic_year_start": {"required": False},
        }

    def validate(self, attrs):
        student_group = attrs.get("student_group")
        if student_group is None and self.instance is not None:
            student_group = self.instance.student_group
        ay = attrs.get("academic_year_start")
        if ay is None and self.instance is not None:
            ay = self.instance.academic_year_start
        if ay is None and student_group is not None:
            ay = student_group.academic_year_start
            attrs["academic_year_start"] = ay
        if student_group is not None and ay is not None:
            if student_group.academic_year_start != ay:
                raise serializers.ValidationError(
                    {
                        "student_group": "Qrupun tədris ili tələbənin ili ilə uyğun olmalıdır.",
                    }
                )
        return attrs

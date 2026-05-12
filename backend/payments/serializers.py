from rest_framework import serializers

from students.serializers import StudentSerializer

from .models import MonthlyPayment


class MonthlyPaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    received_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyPayment
        fields = (
            "id",
            "student",
            "student_name",
            "month",
            "year",
            "amount",
            "payment_date",
            "status",
            "discount",
            "remaining_debt",
            "payment_method",
            "received_by",
            "received_by_name",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_received_by_name(self, obj):
        u = obj.received_by
        if not u:
            return ""
        return u.get_full_name() or u.username


class MonthlyPaymentWriteSerializer(MonthlyPaymentSerializer):
    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated and not validated_data.get(
            "received_by"
        ):
            validated_data["received_by"] = request.user
        return super().create(validated_data)

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AuditLog

User = get_user_model()


class AuditLogSerializer(serializers.ModelSerializer):
    user_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "user",
            "user_display",
            "action",
            "model_name",
            "object_pk",
            "payload",
            "created_at",
        )
        read_only_fields = fields

    def get_user_display(self, obj):
        u = obj.user
        if not u:
            return ""
        return u.get_full_name() or u.username

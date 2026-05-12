from rest_framework import mixins, viewsets

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    filterset_fields = ("model_name", "action", "user")
    ordering_fields = ("created_at",)

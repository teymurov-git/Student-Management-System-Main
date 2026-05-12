from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32)
    model_name = models.CharField(max_length=64)
    object_pk = models.CharField(max_length=64, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["model_name", "-created_at"])]

    def __str__(self):
        return f"{self.action} {self.model_name} {self.object_pk}"

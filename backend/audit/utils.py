from .models import AuditLog


def log_audit(user, action: str, model_name: str, object_pk: str, payload: dict):
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name=model_name,
        object_pk=object_pk or "",
        payload=payload or {},
    )

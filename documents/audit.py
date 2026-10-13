from .models import JournalAudit


def journaliser(request, action, document=None, detail="", utilisateur=None):
    """Enregistre une ligne dans le journal d'audit (traçabilité)."""
    user = utilisateur or getattr(request, "user", None)
    if user is not None and not user.is_authenticated:
        user = None
    JournalAudit.objects.create(
        utilisateur=user,
        document=document,
        numero_document=document.numero if document else "",
        action=action,
        detail=detail[:255],
        adresse_ip=request.META.get("REMOTE_ADDR") or None,
    )

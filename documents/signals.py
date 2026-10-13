from django.contrib.auth.signals import user_logged_in

from .audit import journaliser
from .models import JournalAudit


def _connexion(sender, request, user, **kwargs):
    if request is None:
        return
    journaliser(request, JournalAudit.Action.CONNEXION, utilisateur=user)


user_logged_in.connect(_connexion)

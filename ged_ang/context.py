from django.conf import settings


def globales(request):
    ctx = {
        "GED_NOM": settings.GED_NOM_INSTITUTION,
        "GED_SIGLE": settings.GED_SIGLE,
        "GED_DEVISE": settings.GED_DEVISE,
        "GED_LOGO": settings.GED_LOGO,
        "nb_a_valider": 0,
    }
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.peut_valider:
        from documents.models import Document
        ctx["nb_a_valider"] = (
            Document.objects.visibles_pour(user)
            .filter(statut=Document.Statut.EN_VALIDATION).count()
        )
    return ctx

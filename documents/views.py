from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from comptes.models import Utilisateur

from .audit import journaliser
from .forms import DocumentForm, FiltreForm, VersionForm
from .models import Document, JournalAudit

S = Document.Statut


# ---------- Utilitaires ----------
def _document_visible(request, pk):
    return get_object_or_404(Document.objects.visibles_pour(request.user), pk=pk)


def _modifiable(user, doc):
    """Seul un brouillon peut être modifié (par son auteur ou un administrateur)."""
    return doc.statut == S.BROUILLON and (doc.auteur_id == user.id or user.est_admin_ged)


def _actions_possibles(user, doc):
    actions = []
    if _modifiable(user, doc):
        actions.append(("soumettre", "Soumettre pour validation", "primary"))
    if doc.statut == S.EN_VALIDATION and user.peut_valider:
        actions.append(("valider", "Valider", "success"))
        actions.append(("rejeter", "Rejeter", "danger"))
    if doc.statut == S.VALIDE and user.peut_archiver:
        actions.append(("archiver", "Archiver", "dark"))
    return actions


# ---------- Tableau de bord ----------
@login_required
def accueil(request):
    qs = Document.objects.visibles_pour(request.user)
    comptes = dict(qs.order_by().values_list("statut").annotate(n=Count("pk")))
    par_statut = [(label, comptes.get(code, 0), Document(statut=code).classe_statut)
                  for code, label in S.choices]
    par_type = (qs.order_by().values_list("type_document").annotate(n=Count("pk"))
                .order_by("-n")[:6])
    libelles = dict(Document.Type.choices)
    ctx = {
        "total": qs.count(),
        "par_statut": par_statut,
        "par_type": [(libelles[t], n) for t, n in par_type],
        "recents": qs.select_related("service", "auteur")[:8],
        "mes_brouillons": qs.filter(statut=S.BROUILLON, auteur=request.user)[:5],
        "a_valider": (qs.filter(statut=S.EN_VALIDATION)[:5] if request.user.peut_valider else []),
    }
    return render(request, "documents/accueil.html", ctx)


# ---------- Liste + recherche ----------
@login_required
def liste(request):
    qs = Document.objects.visibles_pour(request.user).select_related("service", "auteur")
    form = FiltreForm(request.GET or None)
    if form.is_valid():
        d = form.cleaned_data
        if d["q"]:
            q = d["q"]
            qs = qs.filter(Q(titre__icontains=q) | Q(numero__icontains=q)
                           | Q(mots_cles__icontains=q) | Q(resume__icontains=q))
        if d["type_document"]:
            qs = qs.filter(type_document=d["type_document"])
        if d["service"]:
            qs = qs.filter(service=d["service"])
        if d["statut"]:
            qs = qs.filter(statut=d["statut"])
        if d["confidentialite"] != "" and d["confidentialite"] is not None:
            qs = qs.filter(confidentialite=int(d["confidentialite"]))
        if d["date_du"]:
            qs = qs.filter(date_document__gte=d["date_du"])
        if d["date_au"]:
            qs = qs.filter(date_document__lte=d["date_au"])
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "documents/liste.html",
                  {"page": page, "form": form, "params": params.urlencode()})


# ---------- Détail ----------
@login_required
def detail(request, pk):
    doc = _document_visible(request, pk)
    journaliser(request, JournalAudit.Action.CONSULTATION, doc)
    versions = list(doc.versions.select_related("auteur"))
    ctx = {
        "doc": doc,
        "versions": versions,
        "derniere": versions[0] if versions else None,
        "modifiable": _modifiable(request.user, doc),
        "actions": _actions_possibles(request.user, doc),
        "historique": (doc.journal.select_related("utilisateur")[:15]
                       if request.user.peut_voir_journal else []),
    }
    return render(request, "documents/detail.html", ctx)


# ---------- Création / modification ----------
@login_required
def creer(request):
    if not request.user.peut_deposer:
        raise PermissionDenied
    form = DocumentForm(request.POST or None, request.FILES or None,
                        user=request.user, creation=True)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            doc = form.save(commit=False)
            doc.auteur = request.user
            doc.save()
            form.save_m2m()
            doc.ajouter_version(form.cleaned_data["fichier"], request.user,
                                form.cleaned_data.get("commentaire", ""))
        journaliser(request, JournalAudit.Action.CREATION, doc, "Version 1")
        messages.success(request, f"Document {doc.numero} créé (brouillon).")
        return redirect("detail", pk=doc.pk)
    return render(request, "documents/formulaire.html",
                  {"form": form, "titre_page": "Déposer un document", "multipart": True})


@login_required
def modifier(request, pk):
    doc = _document_visible(request, pk)
    if not _modifiable(request.user, doc):
        raise PermissionDenied
    form = DocumentForm(request.POST or None, instance=doc, user=request.user, creation=False)
    if request.method == "POST" and form.is_valid():
        form.save()
        journaliser(request, JournalAudit.Action.MODIFICATION, doc, "Métadonnées modifiées")
        messages.success(request, "Métadonnées mises à jour.")
        return redirect("detail", pk=doc.pk)
    return render(request, "documents/formulaire.html",
                  {"form": form, "titre_page": f"Modifier {doc.numero}", "multipart": False})


@login_required
def nouvelle_version(request, pk):
    doc = _document_visible(request, pk)
    if not _modifiable(request.user, doc):
        raise PermissionDenied
    form = VersionForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        v = doc.ajouter_version(form.cleaned_data["fichier"], request.user,
                                form.cleaned_data["commentaire"])
        journaliser(request, JournalAudit.Action.VERSION, doc, f"Version {v.numero}")
        messages.success(request, f"Version {v.numero} ajoutée.")
        return redirect("detail", pk=doc.pk)
    return render(request, "documents/formulaire.html",
                  {"form": form, "titre_page": f"Nouvelle version de {doc.numero}",
                   "multipart": True})


# ---------- Workflow ----------
@login_required
@require_POST
def changer_statut(request, pk, action):
    doc = _document_visible(request, pk)
    autorisees = {a[0] for a in _actions_possibles(request.user, doc)}
    if action not in autorisees:
        raise PermissionDenied
    ancien = doc.get_statut_display()
    if action == "soumettre":
        doc.statut, doc.motif_rejet = S.EN_VALIDATION, ""
    elif action == "valider":
        doc.statut = S.VALIDE
    elif action == "rejeter":
        motif = request.POST.get("motif", "").strip()
        if not motif:
            messages.error(request, "Un motif est obligatoire pour rejeter un document.")
            return redirect("detail", pk=doc.pk)
        doc.statut, doc.motif_rejet = S.BROUILLON, motif
    elif action == "archiver":
        doc.statut = S.ARCHIVE
    doc.save()
    journaliser(request, JournalAudit.Action.STATUT, doc,
                f"{ancien} → {doc.get_statut_display()}" + (
                    f" ({doc.motif_rejet})" if action == "rejeter" else ""))
    messages.success(request, f"Statut : {doc.get_statut_display()}.")
    return redirect("detail", pk=doc.pk)


# ---------- Téléchargement / aperçu (accès contrôlé) ----------
@login_required
def telecharger(request, pk, version):
    doc = _document_visible(request, pk)
    v = get_object_or_404(doc.versions, numero=version)
    inline = request.GET.get("inline") == "1" and v.previsualisable
    journaliser(request, JournalAudit.Action.TELECHARGEMENT, doc,
                f"v{v.numero} {'(aperçu)' if inline else ''}".strip())
    return FileResponse(v.fichier.open("rb"), as_attachment=not inline,
                        filename=v.nom_original)


# ---------- Journal d'audit ----------
@login_required
def journal(request):
    if not request.user.peut_voir_journal:
        raise PermissionDenied
    qs = JournalAudit.objects.select_related("utilisateur")
    action = request.GET.get("action", "")
    utilisateur = request.GET.get("utilisateur", "")
    if action:
        qs = qs.filter(action=action)
    if utilisateur:
        qs = qs.filter(utilisateur_id=utilisateur)
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "documents/journal.html", {
        "page": page, "params": params.urlencode(),
        "actions": JournalAudit.Action.choices,
        "utilisateurs": Utilisateur.objects.order_by("last_name", "username"),
        "action_sel": action, "utilisateur_sel": utilisateur,
    })

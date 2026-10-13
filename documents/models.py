import hashlib
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone


def valider_taille(fichier):
    maximum = settings.GED_TAILLE_MAX_MO * 1024 * 1024
    if fichier.size > maximum:
        raise ValidationError(f"Le fichier dépasse {settings.GED_TAILLE_MAX_MO} Mo.")


def chemin_fichier(instance, nom):
    """Nom de stockage aléatoire (non devinable) ; le nom d'origine est conservé en base."""
    ext = os.path.splitext(nom)[1].lower()
    return f"documents/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class DocumentQuerySet(models.QuerySet):
    def visibles_pour(self, user):
        """Applique la politique d'accès : habilitation, service, partage, brouillons."""
        if not user.is_authenticated:
            return self.none()
        if user.est_admin_ged:
            return self
        niveau = user.niveau_habilitation
        habilite = Q(confidentialite__lte=niveau) | Q(auteur=user)
        acces = (
            Q(confidentialite__lt=Document.Confidentialite.CONFIDENTIEL)
            | Q(auteur=user)
            | Q(pk__in=user.documents_partages.values("pk"))
        )
        if user.service_id:
            acces |= Q(service_id=user.service_id)
        pas_brouillon = ~Q(statut=Document.Statut.BROUILLON) | Q(auteur=user)
        return self.filter(habilite & acces & pas_brouillon)


class Document(models.Model):
    class Type(models.TextChoices):
        LOI = "LOI", "Loi"
        PROJET_LOI = "PROJLOI", "Projet de loi"
        PROPOSITION_LOI = "PROPLOI", "Proposition de loi"
        AMENDEMENT = "AMEND", "Amendement"
        RAPPORT = "RAPPORT", "Rapport de commission"
        COMPTE_RENDU = "CR", "Compte rendu / Procès-verbal"
        RESOLUTION = "RESOL", "Résolution"
        QUESTION = "QUEST", "Question orale / écrite"
        COURRIER = "COURRIER", "Courrier"
        CONVOCATION = "CONVOC", "Convocation / Ordre du jour"
        JOURNAL_OFFICIEL = "JO", "Journal officiel"
        ADMINISTRATIF = "ADMIN", "Document administratif"
        AUTRE = "AUTRE", "Autre"

    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        EN_VALIDATION = "VALIDATION", "En validation"
        VALIDE = "VALIDE", "Validé"
        ARCHIVE = "ARCHIVE", "Archivé"

    class Confidentialite(models.IntegerChoices):
        PUBLIC = 0, "Public"
        INTERNE = 1, "Interne"
        CONFIDENTIEL = 2, "Confidentiel"
        SECRET = 3, "Secret"

    numero = models.CharField("Référence", max_length=30, unique=True, null=True, blank=True,
                              editable=False)
    titre = models.CharField("Titre", max_length=300)
    type_document = models.CharField("Type de document", max_length=10, choices=Type.choices,
                                     default=Type.AUTRE)
    service = models.ForeignKey("comptes.Service", verbose_name="Service / Commission",
                                null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="documents")
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Déposé par",
                               on_delete=models.PROTECT, related_name="documents_deposes")
    date_document = models.DateField("Date du document", default=timezone.localdate)
    legislature = models.CharField("Législature", max_length=60, blank=True)
    session = models.CharField("Session", max_length=60, blank=True)
    resume = models.TextField("Résumé / description", blank=True)
    mots_cles = models.CharField("Mots-clés", max_length=250, blank=True,
                                 help_text="Séparés par des virgules")
    confidentialite = models.PositiveSmallIntegerField(
        "Confidentialité", choices=Confidentialite.choices, default=Confidentialite.INTERNE)
    statut = models.CharField("Statut", max_length=10, choices=Statut.choices,
                              default=Statut.BROUILLON)
    partage_avec = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name="Partagé avec",
                                          blank=True, related_name="documents_partages")
    motif_rejet = models.TextField("Motif du dernier rejet", blank=True)
    cree_le = models.DateTimeField("Créé le", auto_now_add=True)
    modifie_le = models.DateTimeField("Modifié le", auto_now=True)

    objects = DocumentQuerySet.as_manager()

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return f"{self.numero or '—'} · {self.titre}"

    def save(self, *args, **kwargs):
        creation = self.pk is None
        super().save(*args, **kwargs)
        if creation and not self.numero:
            self.numero = f"ANG-{timezone.now():%Y}-{self.pk:05d}"
            super().save(update_fields=["numero"])

    @property
    def classe_statut(self):
        return {
            self.Statut.BROUILLON: "secondary",
            self.Statut.EN_VALIDATION: "warning text-dark",
            self.Statut.VALIDE: "success",
            self.Statut.ARCHIVE: "dark",
        }[self.statut]

    @property
    def classe_confidentialite(self):
        return {0: "success", 1: "info text-dark", 2: "warning text-dark", 3: "danger"}[
            self.confidentialite]

    @property
    def derniere_version(self):
        return self.versions.order_by("-numero").first()

    @transaction.atomic
    def ajouter_version(self, fichier, auteur, commentaire=""):
        sha = hashlib.sha256()
        for morceau in fichier.chunks():
            sha.update(morceau)
        fichier.seek(0)
        dernier = self.versions.order_by("-numero").values_list("numero", flat=True).first() or 0
        return DocumentVersion.objects.create(
            document=self, numero=dernier + 1, fichier=fichier,
            nom_original=os.path.basename(fichier.name), taille=fichier.size,
            empreinte=sha.hexdigest(), commentaire=commentaire, auteur=auteur,
        )


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    numero = models.PositiveIntegerField("Version")
    fichier = models.FileField("Fichier", upload_to=chemin_fichier)
    nom_original = models.CharField("Nom du fichier", max_length=255)
    taille = models.PositiveBigIntegerField("Taille (octets)", default=0)
    empreinte = models.CharField("Empreinte SHA-256", max_length=64)
    commentaire = models.CharField("Commentaire", max_length=255, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                               related_name="versions_deposees")
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-numero"]
        unique_together = [("document", "numero")]
        verbose_name = "Version"
        verbose_name_plural = "Versions"

    def __str__(self):
        return f"{self.document.numero} v{self.numero}"

    @property
    def extension(self):
        return os.path.splitext(self.nom_original)[1].lower().lstrip(".")

    @property
    def previsualisable(self):
        return self.extension in {"pdf", "png", "jpg", "jpeg"}

    @property
    def taille_lisible(self):
        t = float(self.taille)
        for unite in ("o", "Ko", "Mo", "Go"):
            if t < 1024 or unite == "Go":
                return f"{t:.0f} {unite}" if unite == "o" else f"{t:.1f} {unite}"
            t /= 1024


class JournalAudit(models.Model):
    class Action(models.TextChoices):
        CONNEXION = "CONNEXION", "Connexion"
        CONSULTATION = "CONSULT", "Consultation"
        TELECHARGEMENT = "TELECH", "Téléchargement"
        CREATION = "CREATION", "Création"
        MODIFICATION = "MODIF", "Modification"
        VERSION = "VERSION", "Nouvelle version"
        STATUT = "STATUT", "Changement de statut"

    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="actions")
    document = models.ForeignKey(Document, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="journal")
    numero_document = models.CharField(max_length=30, blank=True)
    action = models.CharField(max_length=10, choices=Action.choices)
    detail = models.CharField(max_length=255, blank=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Entrée du journal"
        verbose_name_plural = "Journal d'audit"

    def __str__(self):
        return f"{self.date:%Y-%m-%d %H:%M} {self.utilisateur} {self.get_action_display()}"

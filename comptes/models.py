from django.contrib.auth.models import AbstractUser
from django.db import models


class Service(models.Model):
    class Type(models.TextChoices):
        COMMISSION = "COM", "Commission permanente"
        DIRECTION = "DIR", "Direction / Service administratif"
        GROUPE = "GRP", "Groupe parlementaire"
        CABINET = "CAB", "Cabinet"
        AUTRE = "AUT", "Autre"

    nom = models.CharField("Nom", max_length=200)
    code = models.CharField("Code", max_length=20, unique=True)
    type = models.CharField("Type", max_length=3, choices=Type.choices, default=Type.DIRECTION)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Service / Commission"
        verbose_name_plural = "Services / Commissions"

    def __str__(self):
        return self.nom


class Utilisateur(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur système"
        SG = "SG", "Secrétariat général"
        DEPUTE = "DEPUTE", "Député / Députée"
        COMMISSION = "COMMISSION", "Secrétaire de commission"
        ARCHIVISTE = "ARCHIVISTE", "Archiviste"
        AGENT = "AGENT", "Agent administratif"
        LECTEUR = "LECTEUR", "Lecteur"

    class Habilitation(models.IntegerChoices):
        PUBLIC = 0, "Public"
        INTERNE = 1, "Interne"
        CONFIDENTIEL = 2, "Confidentiel"
        SECRET = 3, "Secret"

    role = models.CharField("Rôle", max_length=12, choices=Role.choices, default=Role.LECTEUR)
    service = models.ForeignKey(Service, verbose_name="Service / Commission",
                                null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="membres")
    fonction = models.CharField("Fonction", max_length=150, blank=True)
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    niveau_habilitation = models.PositiveSmallIntegerField(
        "Niveau d'habilitation", choices=Habilitation.choices, default=Habilitation.INTERNE)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return self.get_full_name() or self.username

    # --- Droits métier ---
    @property
    def est_admin_ged(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def peut_deposer(self):
        return self.role != self.Role.LECTEUR

    @property
    def peut_valider(self):
        return self.est_admin_ged or self.role == self.Role.SG

    @property
    def peut_archiver(self):
        return self.peut_valider or self.role == self.Role.ARCHIVISTE

    @property
    def peut_voir_journal(self):
        return self.peut_archiver

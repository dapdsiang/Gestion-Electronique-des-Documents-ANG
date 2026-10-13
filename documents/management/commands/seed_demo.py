from django.core.management.base import BaseCommand

from comptes.models import Service, Utilisateur

SERVICES = [
    ("SG", "Secrétariat général", "DIR"),
    ("ARCH", "Direction des Archives et de la Documentation", "DIR"),
    ("SLEG", "Direction des Services législatifs", "DIR"),
    ("CAB", "Cabinet du Président de l'Assemblée", "CAB"),
    ("COM-LOIS", "Commission des Lois et de l'Administration", "COM"),
    ("COM-FIN", "Commission des Finances et du Budget", "COM"),
    ("COM-AE", "Commission des Affaires étrangères et de la Défense", "COM"),
]

# (identifiant, prénom, nom, rôle, code service, habilitation, superuser)
UTILISATEURS = [
    ("admin", "Admin", "Système", "ADMIN", "SG", 3, True),
    ("sg", "Secrétaire", "Général", "SG", "SG", 3, False),
    ("archiviste", "Awa", "Archiviste", "ARCHIVISTE", "ARCH", 2, False),
    ("depute", "Député", "Exemple", "DEPUTE", "COM-LOIS", 2, False),
    ("commission", "Secrétaire", "Commission", "COMMISSION", "COM-FIN", 2, False),
    ("agent", "Agent", "Administratif", "AGENT", "SLEG", 1, False),
    ("lecteur", "Simple", "Lecteur", "LECTEUR", None, 0, False),
]


class Command(BaseCommand):
    help = "Crée des services et des comptes de démonstration (NE PAS utiliser en production)."

    def add_arguments(self, parser):
        parser.add_argument("--mot-de-passe", default="Ang@Demo2026!")

    def handle(self, *args, **opts):
        services = {}
        for code, nom, type_ in SERVICES:
            services[code], _ = Service.objects.get_or_create(
                code=code, defaults={"nom": nom, "type": type_})
        for ident, prenom, nom, role, code, niveau, su in UTILISATEURS:
            u, cree = Utilisateur.objects.get_or_create(username=ident, defaults={
                "first_name": prenom, "last_name": nom, "role": role,
                "service": services.get(code), "niveau_habilitation": niveau,
                "is_staff": su, "is_superuser": su,
            })
            if cree:
                u.set_password(opts["mot_de_passe"])
                u.save()
        self.stdout.write(self.style.SUCCESS(
            f"Comptes créés : {', '.join(u[0] for u in UTILISATEURS)} "
            f"— mot de passe : {opts['mot_de_passe']}"))
        self.stdout.write(self.style.WARNING("Changez ces mots de passe immédiatement."))

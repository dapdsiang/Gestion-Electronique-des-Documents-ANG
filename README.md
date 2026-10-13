# GED – Assemblée Nationale de la République de Guinée (ANG)

Application web de **gestion électronique des documents** (Python / Django).

## Fonctionnalités
- Dépôt de documents (lois, projets/propositions de loi, amendements, rapports, comptes rendus, courriers…) avec **référence automatique** `ANG-AAAA-NNNNN`
- **Versionnage** : chaque modification de fichier crée une version (empreinte SHA-256 pour l'intégrité)
- **Workflow de validation** : Brouillon → En validation → Validé → Archivé (rejet avec motif obligatoire) ; un document validé n'est plus modifiable
- **Confidentialité à 4 niveaux** (Public, Interne, Confidentiel, Secret) croisée avec l'habilitation de l'utilisateur, son service/commission et le partage nominatif
- **Rôles** : Administrateur, Secrétariat général, Député, Secrétaire de commission, Archiviste, Agent, Lecteur
- **Recherche multicritères** (texte, type, service, statut, confidentialité, dates) et pagination
- **Aperçu PDF/images** intégré, téléchargement **contrôlé** (les fichiers ne sont jamais accessibles par URL directe)
- **Journal d'audit** (connexions, consultations, téléchargements, créations, changements de statut, IP)
- Interface en français, fuseau Africa/Conakry, interface d'administration Django

## Installation
```bash
python -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations comptes documents
python manage.py migrate
python manage.py seed_demo        # comptes de démonstration (dev uniquement)
python manage.py runserver
```
Ouvrir http://127.0.0.1:8000/ — comptes de démo : `admin`, `sg`, `archiviste`, `depute`,
`commission`, `agent`, `lecteur` (mot de passe : `Ang@Demo2026!` — à changer immédiatement).

## Logo officiel
Le fichier `static/img/logo_ang.svg` est un **logo provisoire**. Pour utiliser le logo officiel de l'ANG :
copiez-le dans `static/img/` (ex. `logo_ang.png`) puis modifiez `GED_LOGO` dans `ged_ang/settings.py`.

## Mise en production (recommandations)
- `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` en variables d'environnement
- PostgreSQL, Gunicorn + Nginx, HTTPS obligatoire, `python manage.py collectstatic` (+ WhiteNoise ou Nginx)
- Stockage `media/` hors de la racine web, sauvegardes chiffrées régulières (base + fichiers)
- Analyse antivirus des dépôts (ClamAV), politique de mots de passe / double authentification
- Bootstrap est chargé via CDN : pour un réseau interne sans Internet, hébergez-le dans `static/`

## Pistes d'évolution
Recherche plein texte dans le contenu (OCR + PostgreSQL FTS / Elasticsearch), signature électronique,
filigrane, durées de conservation et versement aux archives, API REST, notifications par e-mail.

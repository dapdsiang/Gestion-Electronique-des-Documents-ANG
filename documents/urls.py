from django.urls import path

from . import views

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("documents/", views.liste, name="liste"),
    path("documents/nouveau/", views.creer, name="creer"),
    path("documents/<int:pk>/", views.detail, name="detail"),
    path("documents/<int:pk>/modifier/", views.modifier, name="modifier"),
    path("documents/<int:pk>/version/", views.nouvelle_version, name="nouvelle_version"),
    path("documents/<int:pk>/statut/<str:action>/", views.changer_statut, name="changer_statut"),
    path("documents/<int:pk>/fichier/<int:version>/", views.telecharger, name="telecharger"),
    path("journal/", views.journal, name="journal"),
]

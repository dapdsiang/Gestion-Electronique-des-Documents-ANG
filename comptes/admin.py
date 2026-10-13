from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Service, Utilisateur


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("nom", "code", "type")
    list_filter = ("type",)
    search_fields = ("nom", "code")


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ("username", "get_full_name", "role", "service",
                    "niveau_habilitation", "is_active")
    list_filter = ("role", "service", "niveau_habilitation", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Profil GED", {"fields": ("role", "service", "fonction", "telephone",
                                   "niveau_habilitation")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Profil GED", {"fields": ("first_name", "last_name", "email", "role", "service",
                                   "fonction", "niveau_habilitation")}),
    )

from django.contrib import admin

from .models import Document, DocumentVersion, JournalAudit


class VersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    readonly_fields = ("numero", "nom_original", "taille", "empreinte", "auteur", "cree_le")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("numero", "titre", "type_document", "service", "statut",
                    "confidentialite", "auteur", "date_document")
    list_filter = ("type_document", "statut", "confidentialite", "service")
    search_fields = ("numero", "titre", "mots_cles", "resume")
    readonly_fields = ("numero", "cree_le", "modifie_le")
    filter_horizontal = ("partage_avec",)
    inlines = [VersionInline]


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ("date", "utilisateur", "action", "numero_document", "detail", "adresse_ip")
    list_filter = ("action",)
    search_fields = ("numero_document", "detail", "utilisateur__username")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

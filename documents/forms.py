from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator

from comptes.models import Service, Utilisateur

from .models import Document, valider_taille


class StyleMixin:
    def appliquer_style(self):
        for champ in self.fields.values():
            w = champ.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = "form-check-input"
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs["class"] = "form-select"
            else:
                w.attrs["class"] = "form-control"


def champ_fichier(requis=True):
    return forms.FileField(
        label="Fichier", required=requis,
        validators=[FileExtensionValidator(settings.GED_EXTENSIONS), valider_taille],
        help_text=f"Formats : {', '.join(settings.GED_EXTENSIONS)} — max {settings.GED_TAILLE_MAX_MO} Mo",
    )


class DocumentForm(StyleMixin, forms.ModelForm):
    fichier = champ_fichier()
    commentaire = forms.CharField(label="Commentaire de version", required=False,
                                  max_length=255, initial="Version initiale")

    class Meta:
        model = Document
        fields = ["titre", "type_document", "service", "date_document", "legislature",
                  "session", "resume", "mots_cles", "confidentialite", "partage_avec"]
        widgets = {
            "date_document": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "resume": forms.Textarea(attrs={"rows": 3}),
            "partage_avec": forms.SelectMultiple(attrs={"size": 6}),
        }

    def __init__(self, *args, user, creation=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not creation:
            del self.fields["fichier"]
            del self.fields["commentaire"]
        elif user.service_id:
            self.fields["service"].initial = user.service_id
        if not user.est_admin_ged:
            self.fields["confidentialite"].choices = [
                c for c in Document.Confidentialite.choices if c[0] <= user.niveau_habilitation
            ]
        self.fields["partage_avec"].queryset = Utilisateur.objects.filter(
            is_active=True).exclude(pk=user.pk).order_by("last_name", "first_name")
        self.fields["partage_avec"].help_text = (
            "Ctrl/Cmd + clic pour sélectionner plusieurs personnes (utile pour les "
            "documents Confidentiels ou Secrets).")
        self.appliquer_style()


class VersionForm(StyleMixin, forms.Form):
    fichier = champ_fichier()
    commentaire = forms.CharField(label="Commentaire", required=False, max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.appliquer_style()


class FiltreForm(StyleMixin, forms.Form):
    q = forms.CharField(label="Recherche", required=False,
                        widget=forms.TextInput(attrs={"placeholder": "Titre, référence, mot-clé…"}))
    type_document = forms.ChoiceField(label="Type", required=False,
                                      choices=[("", "Tous les types")] + Document.Type.choices)
    service = forms.ModelChoiceField(label="Service", required=False,
                                     queryset=Service.objects.all(), empty_label="Tous les services")
    statut = forms.ChoiceField(label="Statut", required=False,
                               choices=[("", "Tous les statuts")] + Document.Statut.choices)
    confidentialite = forms.ChoiceField(
        label="Confidentialité", required=False,
        choices=[("", "Tous niveaux")] + Document.Confidentialite.choices)
    date_du = forms.DateField(label="Du", required=False,
                              widget=forms.DateInput(attrs={"type": "date"}))
    date_au = forms.DateField(label="Au", required=False,
                              widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.appliquer_style()

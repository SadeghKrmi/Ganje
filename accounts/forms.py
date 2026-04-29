from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import PasswordChangeForm as DjPasswordChangeForm


class EmailAuthenticationForm(forms.Form):
    """Login form using email + password."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "you@example.com",
            "autocomplete": "email",
            "autofocus": True,
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "••••••••",
            "autocomplete": "current-password",
        }),
    )
    remember_me = forms.BooleanField(required=False, initial=True, label="Keep me signed in")

    error_messages = {
        "invalid_login": "Invalid email or password. Please try again.",
        "inactive": "This account is inactive.",
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        password = self.cleaned_data.get("password")
        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(self.error_messages["invalid_login"], code="invalid_login")
            if not self.user_cache.is_active:
                raise forms.ValidationError(self.error_messages["inactive"], code="inactive")
        return self.cleaned_data

    def get_user(self):
        return self.user_cache


class ProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control"}),
            "email":      forms.EmailInput(attrs={"class": "form-control"}),
        }

    def clean_email(self):
        email = (self.cleaned_data["email"] or "").strip().lower()
        UserModel = get_user_model()
        qs = UserModel.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email is already in use by another account.")
        return email


class StyledPasswordChangeForm(DjPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs["class"] = "form-control"

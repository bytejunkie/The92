from django import forms
from django.contrib.auth.forms import UserCreationForm

from allauth.socialaccount.forms import SignupForm as SocialSignupFormBase

from .models import User


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "birthday",
            "favourite_team",
            "password1",
            "password2",
        )
        widgets = {
            "birthday": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "birthday", "favourite_team")
        widgets = {
            "birthday": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }


class SocialSignupForm(SocialSignupFormBase):
    birthday = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Some future features may be age restricted.",
    )
    favourite_team = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="— Select your team —",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from grounds.models import Team
        self.fields["favourite_team"].queryset = Team.objects.order_by("name")

    def save(self, request):
        self.sociallogin.user.birthday = self.cleaned_data["birthday"]
        self.sociallogin.user.favourite_team = self.cleaned_data.get("favourite_team")
        return super().save(request)

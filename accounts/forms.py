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
            "birthday": forms.DateInput(attrs={"type": "date"}),
        }


class SocialSignupForm(SocialSignupFormBase):
    birthday = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Some future features may be age restricted.",
    )

    def save(self, request):
        # Set birthday on the pending user instance before the adapter saves it
        self.sociallogin.user.birthday = self.cleaned_data["birthday"]
        return super().save(request)

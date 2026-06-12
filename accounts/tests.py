import datetime

from django.test import TestCase
from django.urls import reverse

from grounds.models import Ground, Team, Visit

from .models import User, validate_username_comedy
from django.core.exceptions import ValidationError


def make_user(**kwargs):
    defaults = {
        "username": "groundhopper",
        "email": "hop@example.com",
        "birthday": datetime.date(1990, 5, 1),
        "password": "S3cur3Pass!",
    }
    defaults.update(kwargs)
    password = defaults.pop("password")
    user = User(**defaults)
    user.set_password(password)
    user.save()
    return user


class UsernameValidatorTests(TestCase):
    def test_clean_username_accepted(self):
        validate_username_comedy("GroundHopper92")

    def test_profane_username_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_username_comedy("ShitStirrer")
        self.assertEqual(ctx.exception.code, "profane_username")

    def test_profanity_check_is_case_insensitive(self):
        with self.assertRaises(ValidationError):
            validate_username_comedy("WANKER")

    def test_profanity_embedded_in_word_caught(self):
        with self.assertRaises(ValidationError):
            validate_username_comedy("BollocksFC")

    def test_numbers_and_symbols_stripped_before_check(self):
        # "f_u_c_k" normalises to "fuck" — must be blocked
        with self.assertRaises(ValidationError):
            validate_username_comedy("f_u_c_k")

    def test_comedy_name_without_profanity_passes(self):
        validate_username_comedy("BigMac4Ever")


class RegisterViewTests(TestCase):
    URL = "/accounts/register/"

    def _post(self, **overrides):
        data = {
            "username": "NewFan",
            "email": "newfan@example.com",
            "birthday": "1995-06-15",
            "password1": "Str0ngPass!",
            "password2": "Str0ngPass!",
        }
        data.update(overrides)
        return self.client.post(self.URL, data)

    def test_get_renders_form(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")
        self.assertIn("form", response.context)

    def test_valid_registration_creates_user(self):
        self._post()
        self.assertTrue(User.objects.filter(username="NewFan").exists())

    def test_valid_registration_logs_user_in(self):
        self._post()
        response = self.client.get(reverse("grounds:home"))
        self.assertEqual(response.context["user"].username, "NewFan")

    def test_valid_registration_redirects_to_home(self):
        response = self._post()
        self.assertRedirects(response, reverse("grounds:home"))

    def test_profane_username_rejected(self):
        response = self._post(username="twatface")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="twatface").exists())
        self.assertIn("username", response.context["form"].errors)

    def test_duplicate_username_rejected(self):
        make_user(username="NewFan", email="other@example.com")
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="NewFan").count(), 1)

    def test_duplicate_email_rejected(self):
        make_user(username="OtherFan", email="newfan@example.com")
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="NewFan").exists())

    def test_password_mismatch_rejected(self):
        response = self._post(password2="WrongPass!")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="NewFan").exists())

    def test_missing_birthday_rejected(self):
        response = self._post(birthday="")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="NewFan").exists())


class LoginViewTests(TestCase):
    URL = "/accounts/login/"

    def setUp(self):
        self.user = make_user()

    def test_get_renders_form(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)

    def test_valid_credentials_redirect_to_home(self):
        response = self.client.post(
            self.URL,
            {"username": "groundhopper", "password": "S3cur3Pass!"},
        )
        self.assertRedirects(response, reverse("grounds:home"))

    def test_valid_credentials_log_user_in(self):
        self.client.post(
            self.URL,
            {"username": "groundhopper", "password": "S3cur3Pass!"},
        )
        response = self.client.get(reverse("grounds:home"))
        self.assertEqual(response.context["user"].username, "groundhopper")

    def test_wrong_password_rejected(self):
        response = self.client.post(
            self.URL,
            {"username": "groundhopper", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["user"].is_authenticated)

    def test_unknown_user_rejected(self):
        response = self.client.post(
            self.URL,
            {"username": "nobody", "password": "S3cur3Pass!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["user"].is_authenticated)


class LogoutViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_logout_redirects_to_home(self):
        response = self.client.post("/accounts/logout/")
        self.assertRedirects(response, reverse("grounds:home"))

    def test_logout_clears_session(self):
        self.client.post("/accounts/logout/")
        response = self.client.get(reverse("grounds:home"))
        self.assertFalse(response.context["user"].is_authenticated)


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="groundhopper",
            email="hop@example.com",
            birthday=datetime.date(1990, 5, 1),
            password="S3cur3Pass!",
        )
        self.other = User.objects.create_user(
            username="otherfan",
            email="other@example.com",
            birthday=datetime.date(1992, 3, 15),
            password="S3cur3Pass!",
        )
        team = Team.objects.create(
            name="Test FC",
            league_level=Team.LeagueLevel.PREMIER_LEAGUE,
            primary_colour="#FF0000",
        )
        self.ground = Ground.objects.create(
            name="Test Ground", team=team, town_or_city="Testville"
        )

    def test_own_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertRedirects(response, "/accounts/login/")

    def test_own_profile_renders(self):
        self.client.login(username="groundhopper", password="S3cur3Pass!")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "groundhopper")
        self.assertTrue(response.context["is_own_profile"])

    def test_public_profile_accessible_without_login(self):
        response = self.client.get(
            reverse("accounts:profile_user", kwargs={"username": "groundhopper"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "groundhopper")

    def test_public_profile_404_on_unknown_user(self):
        response = self.client.get(
            reverse("accounts:profile_user", kwargs={"username": "nobody"})
        )
        self.assertEqual(response.status_code, 404)

    def test_visited_count_reflects_claims(self):
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        self.client.login(username="groundhopper", password="S3cur3Pass!")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.context["visited_count"], 1)

    def test_repeat_visits_same_ground_counted_once(self):
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        self.client.login(username="groundhopper", password="S3cur3Pass!")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.context["visited_count"], 1)

    def test_other_users_visits_not_shown(self):
        Visit.objects.create(
            user=self.other, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        self.client.login(username="groundhopper", password="S3cur3Pass!")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.context["visited_count"], 0)

    def test_is_own_profile_false_for_public_view(self):
        self.client.login(username="groundhopper", password="S3cur3Pass!")
        response = self.client.get(
            reverse("accounts:profile_user", kwargs={"username": "otherfan"})
        )
        self.assertFalse(response.context["is_own_profile"])


class ProfileTabTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="groundhopper",
            email="hop@example.com",
            birthday=datetime.date(1990, 5, 1),
            password="S3cur3Pass!",
        )
        team = Team.objects.create(
            name="Test FC",
            league_level=Team.LeagueLevel.PREMIER_LEAGUE,
            primary_colour="#FF0000",
        )
        self.ground = Ground.objects.create(
            name="Test Ground", team=team, town_or_city="Testville"
        )
        self.profile_url = reverse("accounts:profile")
        self.client.login(username="groundhopper", password="S3cur3Pass!")

    def test_default_tab_is_visited(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.context["current_tab"], "visited")

    def test_want_to_go_tab(self):
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.WANT_TO_GO
        )
        response = self.client.get(self.profile_url, {"tab": "want-to-go"})
        self.assertEqual(response.context["current_tab"], "want-to-go")
        self.assertEqual(len(response.context["want_to_go"]), 1)

    def test_historic_tab(self):
        Visit.objects.create(
            user=self.user,
            ground=self.ground,
            visit_type=Visit.VisitType.HISTORIC,
            visited_on="2015-03-14",
        )
        response = self.client.get(self.profile_url, {"tab": "historic"})
        self.assertEqual(response.context["current_tab"], "historic")
        self.assertEqual(len(response.context["historic"]), 1)

    def test_invalid_tab_falls_back_to_visited(self):
        response = self.client.get(self.profile_url, {"tab": "nonsense"})
        self.assertEqual(response.context["current_tab"], "visited")

    def test_want_to_go_not_shown_on_visited_tab(self):
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.WANT_TO_GO
        )
        response = self.client.get(self.profile_url, {"tab": "visited"})
        self.assertEqual(response.context["visited_count"], 0)

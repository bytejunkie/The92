import datetime

from django.test import TestCase
from django.urls import reverse

from grounds.models import Event, Ground, Team, Visit

from .models import Follow, User, validate_username_comedy
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

    def test_registration_logs_event(self):
        self._post()
        events = Event.objects.filter(event_type=Event.Type.REGISTER)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.get().user.username, "NewFan")

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

    def test_historic_visit_counts_as_visited(self):
        # Historic visits are folded into the visited grounds (see _VISITED_TYPES),
        # not a separate tab, so one should count toward the visited total.
        Visit.objects.create(
            user=self.user,
            ground=self.ground,
            visit_type=Visit.VisitType.HISTORIC,
            visited_on="2015-03-14",
        )
        response = self.client.get(self.profile_url, {"tab": "visited"})
        self.assertEqual(response.context["current_tab"], "visited")
        self.assertEqual(response.context["visited_count"], 1)

    def test_invalid_tab_falls_back_to_visited(self):
        response = self.client.get(self.profile_url, {"tab": "nonsense"})
        self.assertEqual(response.context["current_tab"], "visited")

    def test_want_to_go_not_shown_on_visited_tab(self):
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.WANT_TO_GO
        )
        response = self.client.get(self.profile_url, {"tab": "visited"})
        self.assertEqual(response.context["visited_count"], 0)


def _make_user(username, email, password="S3cur3Pass!"):
    return User.objects.create_user(
        username=username,
        email=email,
        birthday=datetime.date(1990, 1, 1),
        password=password,
    )


def _make_ground(name="Turf Moor", town="Burnley"):
    team = Team.objects.create(
        name=f"{name} FC",
        league_level=Team.LeagueLevel.CHAMPIONSHIP,
        primary_colour="#5a1a82",
    )
    return Ground.objects.create(name=name, team=team, town_or_city=town)


class FollowModelTests(TestCase):
    def setUp(self):
        self.alice = _make_user("alice", "alice@example.com")
        self.bob = _make_user("bob", "bob@example.com")

    def test_create_follow(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        self.assertEqual(Follow.objects.count(), 1)

    def test_follow_str(self):
        f = Follow.objects.create(follower=self.alice, following=self.bob)
        self.assertIn("alice", str(f))
        self.assertIn("bob", str(f))

    def test_duplicate_follow_raises(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Follow.objects.create(follower=self.alice, following=self.bob)

    def test_follower_count(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        self.assertEqual(Follow.objects.filter(following=self.bob).count(), 1)


class FollowUserViewTests(TestCase):
    def setUp(self):
        self.alice = _make_user("alice", "alice@example.com")
        self.bob = _make_user("bob", "bob@example.com")
        self.client.force_login(self.alice)
        self.follow_url = reverse("accounts:follow", kwargs={"username": "bob"})

    def test_follow_creates_relationship(self):
        self.client.post(self.follow_url)
        self.assertTrue(Follow.objects.filter(follower=self.alice, following=self.bob).exists())

    def test_follow_logs_event_with_context(self):
        self.client.post(self.follow_url)
        event = Event.objects.get(event_type=Event.Type.FOLLOW)
        self.assertEqual(event.user, self.alice)
        self.assertEqual(event.context.get("followed"), "bob")

    def test_unfollow_does_not_log(self):
        self.client.post(self.follow_url)  # follow
        self.client.post(self.follow_url)  # unfollow
        self.assertEqual(Event.objects.filter(event_type=Event.Type.FOLLOW).count(), 1)

    def test_follow_redirects_to_profile(self):
        response = self.client.post(self.follow_url)
        self.assertRedirects(
            response,
            reverse("accounts:profile_user", kwargs={"username": "bob"}),
        )

    def test_unfollow_removes_relationship(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        self.client.post(self.follow_url)
        self.assertFalse(Follow.objects.filter(follower=self.alice, following=self.bob).exists())

    def test_cannot_follow_self(self):
        self_url = reverse("accounts:follow", kwargs={"username": "alice"})
        self.client.post(self_url)
        self.assertFalse(Follow.objects.filter(follower=self.alice, following=self.alice).exists())

    def test_follow_requires_login(self):
        self.client.logout()
        response = self.client.post(self.follow_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Follow.objects.exists())

    def test_get_request_redirects(self):
        response = self.client.get(self.follow_url)
        self.assertRedirects(
            response,
            reverse("accounts:profile_user", kwargs={"username": "bob"}),
        )

    def test_follower_count_shown_on_profile(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        response = self.client.get(
            reverse("accounts:profile_user", kwargs={"username": "bob"})
        )
        self.assertEqual(response.context["follower_count"], 1)


class EditProfileViewTests(TestCase):
    def setUp(self):
        self.user = _make_user("groundhopper", "hop@example.com")
        self.client.force_login(self.user)
        self.url = reverse("accounts:edit_profile")

    def test_get_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/edit_profile.html")
        self.assertIn("form", response.context)

    def test_edit_profile_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_valid_post_updates_username(self):
        self.client.post(
            self.url,
            {
                "username": "hopper92",
                "birthday": "1990-01-01",
                "favourite_team": "",
            },
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "hopper92")

    def test_valid_post_redirects_to_profile(self):
        response = self.client.post(
            self.url,
            {
                "username": "hopper92",
                "birthday": "1990-01-01",
                "favourite_team": "",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))

    def test_invalid_post_rerenders_form(self):
        response = self.client.post(self.url, {"username": "", "birthday": ""})
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)


class FeedViewTests(TestCase):
    def setUp(self):
        self.alice = _make_user("alice", "alice@example.com")
        self.bob = _make_user("bob", "bob@example.com")
        self.ground = _make_ground()
        self.client.force_login(self.alice)
        self.url = reverse("accounts:feed")

    def test_feed_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_feed_empty_when_not_following(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["following_count"], 0)

    def test_feed_shows_followed_user_visits(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        Visit.objects.create(
            user=self.bob, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["visits"]), 1)

    def test_feed_excludes_own_visits(self):
        Visit.objects.create(
            user=self.alice, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["visits"]), 0)

    def test_feed_excludes_want_to_go_visits(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        Visit.objects.create(
            user=self.bob, ground=self.ground, visit_type=Visit.VisitType.WANT_TO_GO
        )
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["visits"]), 0)


class WishlistPrivacyTests(TestCase):
    def setUp(self):
        self.owner = _make_user("owner", "owner@example.com")
        self.follower = _make_user("follower", "follower@example.com")
        self.stranger = _make_user("stranger", "stranger@example.com")
        self.ground = _make_ground()
        Visit.objects.create(
            user=self.owner, ground=self.ground, visit_type=Visit.VisitType.WANT_TO_GO
        )
        self.profile_url = reverse(
            "accounts:profile_user", kwargs={"username": "owner"}
        )

    def test_owner_can_see_wishlist(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.profile_url, {"tab": "want-to-go"})
        self.assertTrue(response.context["can_see_wishlist"])
        self.assertEqual(response.context["current_tab"], "want-to-go")

    def test_follower_can_see_wishlist(self):
        Follow.objects.create(follower=self.follower, following=self.owner)
        self.client.force_login(self.follower)
        response = self.client.get(self.profile_url, {"tab": "want-to-go"})
        self.assertTrue(response.context["can_see_wishlist"])
        self.assertEqual(response.context["current_tab"], "want-to-go")

    def test_stranger_cannot_see_wishlist_tab(self):
        self.client.force_login(self.stranger)
        response = self.client.get(self.profile_url, {"tab": "want-to-go"})
        self.assertFalse(response.context["can_see_wishlist"])
        self.assertEqual(response.context["current_tab"], "visited")

    def test_anonymous_cannot_see_wishlist_tab(self):
        response = self.client.get(self.profile_url, {"tab": "want-to-go"})
        self.assertFalse(response.context["can_see_wishlist"])
        self.assertEqual(response.context["current_tab"], "visited")


class LeaderboardViewTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:leaderboard")
        self.alice = _make_user("alice", "alice@example.com")
        self.bob = _make_user("bob", "bob@example.com")
        self.carol = _make_user("carol", "carol@example.com")

    def _visit(self, user, n, prefix, visit_type=Visit.VisitType.VISITED):
        for i in range(n):
            ground = _make_ground(name=f"{prefix}{i}", town="Town")
            Visit.objects.create(user=user, ground=ground, visit_type=visit_type)

    def test_global_ranks_by_visits_desc(self):
        self._visit(self.alice, 3, "A")
        self._visit(self.bob, 1, "B")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        players = list(response.context["page_obj"])
        self.assertEqual(players[0], self.alice)
        self.assertEqual(players[0].visited, 3)
        self.assertEqual(players[1], self.bob)

    def test_users_without_visits_excluded(self):
        self._visit(self.alice, 1, "A")
        response = self.client.get(self.url)
        usernames = [p.username for p in response.context["page_obj"]]
        self.assertIn("alice", usernames)
        self.assertNotIn("carol", usernames)

    def test_historic_visits_count_toward_score(self):
        self._visit(self.alice, 2, "H", visit_type=Visit.VisitType.HISTORIC)
        response = self.client.get(self.url)
        self.assertEqual(response.context["page_obj"][0].visited, 2)

    def test_want_to_go_does_not_count(self):
        self._visit(self.alice, 2, "W", visit_type=Visit.VisitType.WANT_TO_GO)
        response = self.client.get(self.url)
        self.assertNotIn("alice", [p.username for p in response.context["page_obj"]])

    def test_unauthenticated_can_view(self):
        self._visit(self.alice, 1, "A")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["my_rank"])

    def test_my_rank_reported(self):
        self._visit(self.alice, 2, "A")
        self._visit(self.bob, 1, "B")
        self.client.force_login(self.bob)
        response = self.client.get(self.url)
        self.assertEqual(response.context["my_rank"], 2)
        self.assertEqual(response.context["my_visited"], 1)

    def test_friends_scope_limits_to_followed_plus_self(self):
        self._visit(self.alice, 1, "A")
        self._visit(self.bob, 1, "B")
        self._visit(self.carol, 5, "C")  # high score but not followed
        Follow.objects.create(follower=self.alice, following=self.bob)
        self.client.force_login(self.alice)
        response = self.client.get(self.url, {"scope": "friends"})
        usernames = [p.username for p in response.context["page_obj"]]
        self.assertIn("alice", usernames)
        self.assertIn("bob", usernames)
        self.assertNotIn("carol", usernames)

    def test_friends_scope_falls_back_to_global_when_anonymous(self):
        response = self.client.get(self.url, {"scope": "friends"})
        self.assertEqual(response.context["scope"], "global")


class SignatureImageTests(TestCase):
    def setUp(self):
        self.user = _make_user("siguser", "sig@example.com")
        self.url = reverse("accounts:signature_image", kwargs={"username": "siguser"})

    def test_returns_png(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertTrue(response.content.startswith(b"\x89PNG"))

    def test_dark_variant_returns_png(self):
        response = self.client.get(self.url, {"theme": "dark"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    def test_unknown_user_404(self):
        response = self.client.get(
            reverse("accounts:signature_image", kwargs={"username": "ghost"})
        )
        self.assertEqual(response.status_code, 404)

    def test_renders_with_team_and_visits(self):
        team = Team.objects.create(name="Leeds United", primary_colour="#1D428A")
        self.user.favourite_team = team
        self.user.save()
        ground = _make_ground(name="Elland Road", town="Leeds")
        Visit.objects.create(user=self.user, ground=ground, visit_type=Visit.VisitType.VISITED)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"\x89PNG"))


class ShareForumCodesTests(TestCase):
    def setUp(self):
        self.user = _make_user("sharer", "sharer@example.com")
        self.url = reverse("accounts:share_profile", kwargs={"username": "sharer"})

    def test_share_page_exposes_forum_embed_codes(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("signature.png", response.context["sig_url"])
        self.assertIn("[img]", response.context["forum_light"]["bbcode"])
        self.assertIn("<img", response.context["forum_light"]["html"])
        self.assertIn("theme=dark", response.context["forum_dark"]["bbcode"])

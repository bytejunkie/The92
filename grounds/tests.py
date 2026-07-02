from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Ground, Team, Visit

User = get_user_model()


def make_team(**kwargs):
    defaults = {
        "name": "Test FC",
        "league_level": Team.LeagueLevel.PREMIER_LEAGUE,
        "is_current_92": True,
        "primary_colour": "#FF0000",
    }
    defaults.update(kwargs)
    return Team.objects.create(**defaults)


def make_ground(team=None, **kwargs):
    if team is None:
        team = make_team()
    defaults = {
        "name": "Test Ground",
        "team": team,
        "town_or_city": "Testville",
        "capacity": 20000,
        "opened_year": 1950,
    }
    defaults.update(kwargs)
    return Ground.objects.create(**defaults)


def make_user(username="groundhopper", **kwargs):
    defaults = {
        "email": f"{username}@test.com",
        "password": "testpass123",
        "birthday": "1990-01-01",
    }
    defaults.update(kwargs)
    return User.objects.create_user(username=username, **defaults)


class GroundListViewTests(TestCase):
    def setUp(self):
        pl_team = make_team(name="PL Club", league_level=Team.LeagueLevel.PREMIER_LEAGUE)
        champ_team = make_team(name="Champ Club", league_level=Team.LeagueLevel.CHAMPIONSHIP)
        self.pl_ground = make_ground(team=pl_team, name="Premier Park")
        self.champ_ground = make_ground(team=champ_team, name="Championship Arena")

    def test_list_shows_all_grounds(self):
        response = self.client.get(reverse("grounds:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premier Park")
        self.assertContains(response, "Championship Arena")

    def test_league_filter(self):
        response = self.client.get(reverse("grounds:list"), {"league": "premier-league"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premier Park")
        self.assertNotContains(response, "Championship Arena")

    def test_search_by_ground_name(self):
        response = self.client.get(reverse("grounds:list"), {"q": "Premier"})
        self.assertContains(response, "Premier Park")
        self.assertNotContains(response, "Championship Arena")

    def test_search_by_team_name(self):
        response = self.client.get(reverse("grounds:list"), {"q": "Champ Club"})
        self.assertNotContains(response, "Premier Park")
        self.assertContains(response, "Championship Arena")

    def test_search_and_filter_combined(self):
        response = self.client.get(
            reverse("grounds:list"), {"league": "championship", "q": "Arena"}
        )
        self.assertNotContains(response, "Premier Park")
        self.assertContains(response, "Championship Arena")

    def test_search_no_results(self):
        response = self.client.get(reverse("grounds:list"), {"q": "doesnotexist"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No grounds found")

    def test_invalid_league_ignored(self):
        response = self.client.get(reverse("grounds:list"), {"league": "fake-league"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premier Park")
        self.assertContains(response, "Championship Arena")


class GroundDetailViewTests(TestCase):
    def setUp(self):
        self.ground = make_ground()
        self.url = reverse("grounds:detail", kwargs={"slug": self.ground.slug})

    def test_detail_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ground.name)

    def test_detail_404_on_bad_slug(self):
        response = self.client.get(
            reverse("grounds:detail", kwargs={"slug": "no-such-ground"})
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_shows_zero_visitors_initially(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["visit_count"], 0)

    def test_detail_user_has_visited_false_for_anonymous(self):
        response = self.client.get(self.url)
        self.assertFalse(response.context["user_has_visited"])


class VisitModelTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.ground = make_ground()

    def test_create_visited(self):
        visit = Visit.objects.create(
            user=self.user,
            ground=self.ground,
            visit_type=Visit.VisitType.VISITED,
        )
        self.assertEqual(visit.visit_type, Visit.VisitType.VISITED)

    def test_multiple_visited_entries_allowed(self):
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        self.assertEqual(
            Visit.objects.filter(user=self.user, ground=self.ground).count(), 2
        )

    def test_duplicate_want_to_go_raises_integrity_error(self):
        from django.db import IntegrityError

        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.WANT_TO_GO
        )
        with self.assertRaises(IntegrityError):
            Visit.objects.create(
                user=self.user,
                ground=self.ground,
                visit_type=Visit.VisitType.WANT_TO_GO,
            )

    def test_str(self):
        visit = Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        self.assertIn(self.ground.name, str(visit))


class ClaimGroundViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.ground = make_ground()
        self.claim_url = reverse("grounds:claim", kwargs={"slug": self.ground.slug})
        self.detail_url = reverse("grounds:detail", kwargs={"slug": self.ground.slug})

    def test_post_creates_visit(self):
        self.client.login(username="groundhopper", password="testpass123")
        response = self.client.post(self.claim_url)
        # Claim redirects back with ?claimed=1 to trigger the share prompt.
        self.assertRedirects(response, self.detail_url + "?claimed=1")
        self.assertEqual(
            Visit.objects.filter(
                user=self.user,
                ground=self.ground,
                visit_type=Visit.VisitType.VISITED,
            ).count(),
            1,
        )

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.post(self.claim_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_get_request_redirects_to_detail(self):
        self.client.login(username="groundhopper", password="testpass123")
        response = self.client.get(self.claim_url)
        self.assertRedirects(response, self.detail_url)

    def test_claiming_twice_creates_two_visits(self):
        self.client.login(username="groundhopper", password="testpass123")
        self.client.post(self.claim_url)
        self.client.post(self.claim_url)
        self.assertEqual(
            Visit.objects.filter(
                user=self.user,
                ground=self.ground,
                visit_type=Visit.VisitType.VISITED,
            ).count(),
            2,
        )

    def test_detail_shows_visited_state_after_claim(self):
        self.client.login(username="groundhopper", password="testpass123")
        Visit.objects.create(
            user=self.user,
            ground=self.ground,
            visit_type=Visit.VisitType.VISITED,
        )
        response = self.client.get(self.detail_url)
        self.assertTrue(response.context["user_has_visited"])

    def test_detail_unvisited_for_different_user(self):
        other = make_user(username="otherfan")
        Visit.objects.create(
            user=self.user,
            ground=self.ground,
            visit_type=Visit.VisitType.VISITED,
        )
        self.client.login(username="otherfan", password="testpass123")
        response = self.client.get(self.detail_url)
        self.assertFalse(response.context["user_has_visited"])

    def test_visit_count_increments(self):
        other = make_user(username="otherfan")
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        Visit.objects.create(
            user=other, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        response = self.client.get(self.detail_url)
        self.assertEqual(response.context["visit_count"], 2)


class GroundListVisitedStateTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.ground = make_ground()
        self.other_ground = make_ground(
            team=make_team(name="Other FC"), name="Other Ground"
        )
        self.list_url = reverse("grounds:list")

    def test_visited_ground_ids_empty_for_anonymous(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.context["visited_ground_ids"], set())

    def test_visited_ground_ids_contains_claimed_ground(self):
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        self.client.login(username="groundhopper", password="testpass123")
        response = self.client.get(self.list_url)
        self.assertIn(self.ground.id, response.context["visited_ground_ids"])

    def test_visited_ground_ids_excludes_unvisited(self):
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        self.client.login(username="groundhopper", password="testpass123")
        response = self.client.get(self.list_url)
        self.assertNotIn(self.other_ground.id, response.context["visited_ground_ids"])


class HomeViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.ground = make_ground()

    def test_visited_count_zero_for_anonymous(self):
        response = self.client.get(reverse("grounds:home"))
        self.assertEqual(response.context["visited_count"], 0)

    def test_visited_count_reflects_real_visits(self):
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        self.client.login(username="groundhopper", password="testpass123")
        response = self.client.get(reverse("grounds:home"))
        self.assertEqual(response.context["visited_count"], 1)

    def test_repeat_visits_same_ground_count_once(self):
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        self.client.login(username="groundhopper", password="testpass123")
        response = self.client.get(reverse("grounds:home"))
        self.assertEqual(response.context["visited_count"], 1)


class WantGroundViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.ground = make_ground()
        self.want_url = reverse("grounds:want", kwargs={"slug": self.ground.slug})
        self.detail_url = reverse("grounds:detail", kwargs={"slug": self.ground.slug})

    def test_post_creates_want_to_go(self):
        self.client.login(username="groundhopper", password="testpass123")
        self.client.post(self.want_url)
        self.assertTrue(
            Visit.objects.filter(
                user=self.user, ground=self.ground, visit_type=Visit.VisitType.WANT_TO_GO
            ).exists()
        )

    def test_post_again_removes_want_to_go(self):
        self.client.login(username="groundhopper", password="testpass123")
        self.client.post(self.want_url)
        self.client.post(self.want_url)
        self.assertFalse(
            Visit.objects.filter(
                user=self.user, ground=self.ground, visit_type=Visit.VisitType.WANT_TO_GO
            ).exists()
        )

    def test_redirects_to_detail(self):
        self.client.login(username="groundhopper", password="testpass123")
        response = self.client.post(self.want_url)
        self.assertRedirects(response, self.detail_url)

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.post(self.want_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_detail_context_reflects_want_state(self):
        self.client.login(username="groundhopper", password="testpass123")
        self.client.post(self.want_url)
        response = self.client.get(self.detail_url)
        self.assertTrue(response.context["user_wants_to_go"])

    def test_detail_context_false_after_toggle_off(self):
        self.client.login(username="groundhopper", password="testpass123")
        self.client.post(self.want_url)
        self.client.post(self.want_url)
        response = self.client.get(self.detail_url)
        self.assertFalse(response.context["user_wants_to_go"])


class DeleteVisitViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user(username="otherfan")
        self.ground = make_ground()
        self.visit = Visit.objects.create(
            user=self.user, ground=self.ground, visit_type=Visit.VisitType.VISITED
        )
        self.delete_url = reverse("grounds:delete_visit", kwargs={"pk": self.visit.pk})

    def test_get_shows_confirmation_page(self):
        self.client.login(username="groundhopper", password="testpass123")
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ground.name)

    def test_post_deletes_visit(self):
        self.client.login(username="groundhopper", password="testpass123")
        self.client.post(self.delete_url)
        self.assertFalse(Visit.objects.filter(pk=self.visit.pk).exists())

    def test_post_redirects_to_profile(self):
        self.client.login(username="groundhopper", password="testpass123")
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, reverse("accounts:profile"))

    def test_cannot_delete_another_users_visit(self):
        self.client.login(username="otherfan", password="testpass123")
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Visit.objects.filter(pk=self.visit.pk).exists())

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

from datetime import UTC, datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase
from django.utils import timezone

from app.detail_builders import _build_detail_link_sections, _build_detail_person_rows
from app.models import (
    CreditRoleType,
    Item,
    ItemPersonCredit,
    MediaTypes,
    Movie,
    Person,
    Sources,
    Status,
)


class GameCastRowFromCreditsTests(TestCase):
    def setUp(self):
        self.item = Item.objects.create(
            media_id="igdb-1",
            source=Sources.IGDB.value,
            media_type=MediaTypes.GAME.value,
            title="Dispatch",
            image="http://example.com/game.jpg",
            provider_external_ids={"imdb_id": "tt1111111"},
        )
        self.actor = Person.objects.create(
            source=Sources.IMDB.value,
            source_person_id="nm0000001",
            name="Alice Actor",
            image="http://example.com/alice.jpg",
        )
        self.director = Person.objects.create(
            source=Sources.IMDB.value,
            source_person_id="nm0000002",
            name="Bob Director",
        )
        ItemPersonCredit.objects.create(
            item=self.item,
            person=self.actor,
            role_type=CreditRoleType.CAST.value,
            role="Sam",
            sort_order=1,
        )
        ItemPersonCredit.objects.create(
            item=self.item,
            person=self.director,
            role_type=CreditRoleType.CREW.value,
            role="Director",
            department="Directing",
            sort_order=2,
        )

    def test_cast_and_crew_rows_populate_from_item_person_credit(self):
        rows = _build_detail_person_rows({"media_id": "igdb-1"}, item=self.item)

        cast_items = rows["cast_row"]["items"]
        crew_items = rows["crew_row"]["items"]
        self.assertEqual(len(cast_items), 1)
        self.assertEqual(cast_items[0]["name"], "Alice Actor")
        self.assertEqual(cast_items[0]["role"], "Sam")
        self.assertEqual(len(crew_items), 1)
        self.assertEqual(crew_items[0]["name"], "Bob Director")

    def test_cast_entries_omit_person_id_to_avoid_broken_profile_links(self):
        rows = _build_detail_person_rows({"media_id": "igdb-1"}, item=self.item)

        for entry in rows["cast_row"]["items"] + rows["crew_row"]["items"]:
            self.assertNotIn("person_id", entry)

    def test_non_game_items_are_unaffected(self):
        movie_item = Item.objects.create(
            media_id="tmdb-1",
            source=Sources.TMDB.value,
            media_type=MediaTypes.MOVIE.value,
            title="A Movie",
            image="http://example.com/movie.jpg",
        )
        rows = _build_detail_person_rows({"media_id": "tmdb-1"}, item=movie_item)
        self.assertEqual(rows["cast_row"]["items"], [])
        self.assertEqual(rows["crew_row"]["items"], [])

    def test_existing_media_metadata_cast_takes_priority_over_credits(self):
        media_metadata = {
            "media_id": "igdb-1",
            "cast": [{"person_id": "1", "name": "From Metadata"}],
        }
        rows = _build_detail_person_rows(media_metadata, item=self.item)
        self.assertEqual(rows["cast_row"]["items"][0]["name"], "From Metadata")


class DetailPersonCreditEnrichmentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="credit-user",
            password="test-password",
        )
        self.person = Person.objects.create(
            source=Sources.TMDB.value,
            source_person_id="person-1",
            name="Known Actor",
            birth_date="1990-07-01",
        )
        self.current_item = Item.objects.create(
            media_id="current",
            source=Sources.TMDB.value,
            media_type=MediaTypes.MOVIE.value,
            title="Current Film",
            release_datetime=datetime(2024, 6, 1, tzinfo=UTC),
        )

    def test_rows_show_age_and_top_watched_known_for_titles(self):
        historical_titles = [
            ("watched-1", "Watched One", 8.0),
            ("watched-2", "Watched Two", 9.0),
            ("watched-3", "Watched Three", 7.0),
            ("watched-4", "Watched Four", 10.0),
        ]
        for media_id, title, rating in historical_titles:
            item = Item.objects.create(
                media_id=media_id,
                source=Sources.TMDB.value,
                media_type=MediaTypes.MOVIE.value,
                title=title,
                provider_rating=rating,
                provider_rating_count=100,
            )
            ItemPersonCredit.objects.create(
                item=item,
                person=self.person,
                role_type=CreditRoleType.CAST.value,
                role="Lead",
            )
            Movie.objects.create(
                item=item,
                user=self.user,
                status=Status.PLANNING.value,
                start_date=timezone.now(),
                end_date=timezone.now(),
            )

        self.user.person_known_for_limit = 3
        rows = _build_detail_person_rows(
            {
                "source": Sources.TMDB.value,
                "details": {"release_date": "2024-06-01"},
                "cast": [
                    {
                        "person_id": "person-1",
                        "name": "Known Actor",
                        "image": "https://example.com/person.jpg",
                        "role": "Lead",
                    },
                ],
            },
            item=self.current_item,
            user=self.user,
        )

        person_row = rows["cast_row"]["items"][0]
        self.assertEqual(person_row["age_at_credit"], 33)
        self.assertEqual(
            [entry["title"] for entry in person_row["known_for"]],
            ["Watched Four", "Watched Two", "Watched One"],
        )

    def test_person_card_renders_age_and_known_for_under_the_poster(self):
        person_row = {
            "person_id": "person-1",
            "name": "Known Actor",
            "image": "https://example.com/person.jpg",
            "role": "Lead",
            "age_at_credit": 33,
            "known_for": [
                {
                    "source": Sources.TMDB.value,
                    "media_type": MediaTypes.MOVIE.value,
                    "media_id": "watched-1",
                    "title": "Watched One",
                    "image": "https://example.com/movie.jpg",
                },
            ],
        }

        html = render_to_string(
            "app/components/person_card_inline.html",
            {
                "person": person_row,
                "media": {"source": Sources.TMDB.value},
                "user": self.user,
                "IMG_NONE": settings.IMG_NONE,
            },
        )

        self.assertLess(
            html.index('data-src="https://example.com/person.jpg"'),
            html.index("Age 33"),
        )
        self.assertLess(html.index("Age 33"), html.index("Your history"))
        self.assertIn("Watched One", html)
        self.assertIn('data-person-credit-card="true"', html)
        self.assertIn('data-person-credit-details="true"', html)
        self.assertNotIn("search-result-card", html)



class GameImdbLinkChipTests(TestCase):
    def test_imdb_chip_appears_when_resolved(self):
        item = Item.objects.create(
            media_id="igdb-2",
            source=Sources.IGDB.value,
            media_type=MediaTypes.GAME.value,
            title="Dispatch",
            image="http://example.com/game.jpg",
            provider_external_ids={"imdb_id": "tt34996965"},
        )
        sections = _build_detail_link_sections(
            {"media_id": "igdb-2"},
            MediaTypes.GAME.value,
            Sources.IGDB.value,
            Sources.IGDB.value,
            item=item,
        )
        external_section = next(s for s in sections if s["title"] == "External links")
        imdb_entry = next(
            e for e in external_section["entries"] if e["label"] == "IMDb"
        )
        self.assertEqual(imdb_entry["url"], "https://www.imdb.com/title/tt34996965/")

    def test_no_imdb_chip_when_unresolved(self):
        item = Item.objects.create(
            media_id="igdb-3",
            source=Sources.IGDB.value,
            media_type=MediaTypes.GAME.value,
            title="Some Unmatched Game",
            image="http://example.com/game.jpg",
        )
        sections = _build_detail_link_sections(
            {"media_id": "igdb-3"},
            MediaTypes.GAME.value,
            Sources.IGDB.value,
            Sources.IGDB.value,
            item=item,
        )
        for section in sections:
            for entry in section["entries"]:
                self.assertNotEqual(entry["label"], "IMDb")

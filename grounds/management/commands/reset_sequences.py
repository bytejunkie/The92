"""Reset database primary-key sequences to MAX(id).

Loading rows with explicit primary keys (``loaddata``, ``bulk_create`` from a
dump, etc.) does NOT advance Postgres' auto-increment sequences, so the next
INSERT reuses low ids and fails with a duplicate-key IntegrityError (e.g. a
ground claim creating a Visit). Run this once after any such bulk import:

    python manage.py reset_sequences
"""
from django.apps import apps
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import connection


class Command(BaseCommand):
    help = "Reset all PK sequences to MAX(id). Run after a bulk data import."

    def handle(self, *args, **options):
        sql_list = connection.ops.sequence_reset_sql(no_style(), apps.get_models())
        with connection.cursor() as cursor:
            for sql in sql_list:
                cursor.execute(sql)
        self.stdout.write(
            self.style.SUCCESS(f"Reset {len(sql_list)} sequence(s) to MAX(id).")
        )

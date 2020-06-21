from copy import copy
from datetime import datetime
from unittest import mock

import django
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from tests.testapp.models import ModifiableDatetimeModel

from django_mysql.models import DateTimeField


class TestModifiableDatetimeField(TestCase):
    def test_default_on_update_current_timestamp_option(self):
        field = DateTimeField()
        assert field.on_update_current_timestamp is False

    def test_auto_now_and_on_update_current_timestamp_option_are_mutually_exclusive(
        self,
    ):
        field = DateTimeField(auto_now=True, on_update_current_timestamp=True)
        errors = field.check()
        assert errors[0].id == "Error"

    def test_datetime_field_does_not_support_auto_now_add_option(self,):
        field = DateTimeField(auto_now_add=True)
        errors = field.check()
        assert errors[0].id == "Error"

    def test_allow_datetime_field_argument(self):
        field1 = DateTimeField(on_update_current_timestamp=True)
        field2 = DateTimeField(auto_now=True, on_update_current_timestamp=False)
        field3 = DateTimeField(default=timezone.now, on_update_current_timestamp=False)
        assert hasattr(field1, "on_update_current_timestamp")
        assert hasattr(field2, "auto_now")
        assert hasattr(field3, "default")

    @mock.patch(
        "django.db.models.fields.timezone.now", return_value=datetime(2020, 6, 13)
    )
    def test_save_modifiable_datetime_field_should_be_save_with_django_timezone_now(
        self, _,
    ):
        s1 = ModifiableDatetimeModel.objects.create(model_char="test_char",)
        with mock.patch(
            "django.db.models.fields.timezone.now", return_value=datetime(2020, 6, 14)
        ):
            s2 = copy(s1)
            s2.model_char = "updated_char"
            s2.save()

        assert s1.datetime1 == s2.datetime1
        assert s1.datetime2 == s2.datetime2
        assert s1.datetime3 == s2.datetime3

    @mock.patch(
        "django.db.models.fields.timezone.now", return_value=datetime(2020, 6, 13)
    )
    def test_update_modifiable_datetime_field_should_be_updated_to_current_timestamp(
        self, _,
    ):
        s1 = ModifiableDatetimeModel.objects.create(
            model_char="test_char", on_update_datetime=datetime(2020, 6, 13),
        )
        with mock.patch(
            "django.db.models.fields.timezone.now", return_value=datetime(2020, 6, 14)
        ):
            ModifiableDatetimeModel.objects.filter(id=s1.id).update(
                model_char="updated_char"
            )

        s2 = ModifiableDatetimeModel.objects.get(id=s1.id)
        assert s1.datetime1 != s2.datetime1
        assert s1.datetime2 == s2.datetime2
        assert s1.datetime3 == s2.datetime3


class TestCheck(TestCase):

    if django.VERSION >= (2, 2):
        databases = ["default", "other"]
    else:
        multi_db = True

    def test_check(self):
        errors = ModifiableDatetimeModel.check()
        assert errors == []


class TestDeconstruct(TestCase):
    def test_deconstruct(self):
        field = DateTimeField()
        name, path, args, kwargs = field.deconstruct()
        assert path == "django_mysql.models.DatetimeField"
        assert "on_update_current_timestamp" in kwargs


class TestMigrations(TransactionTestCase):
    @override_settings(
        MIGRATION_MODULES={"testapp": "tests.testapp.datetime_default_migrations"}
    )
    def test_adding_field_with_default(self):
        table_name = "testapp_modifiabledatetimemodel"
        table_names = connection.introspection.table_names
        with connection.cursor() as cursor:
            assert table_name not in table_names(cursor)

        call_command(
            "migrate", "testapp", verbosity=0, skip_checks=True, interactive=False
        )
        with connection.cursor() as cursor:
            assert table_name in table_names(cursor)

        call_command(
            "migrate",
            "testapp",
            "zero",
            verbosity=0,
            skip_checks=True,
            interactive=False,
        )
        with connection.cursor() as cursor:
            assert table_name not in table_names(cursor)

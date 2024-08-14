# Generated by Django 4.1.4 on 2023-01-03 21:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("typeclasses", "0016_alter_attribute_id_alter_tag_id"),
        ("objects", "0013_defaultobject_alter_objectdb_id_defaultcharacter_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Scene",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("db_title", models.TextField(blank=True, verbose_name="title")),
                ("db_content", models.TextField(blank=True, verbose_name="content")),
                (
                    "db_date_created",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="date created"
                    ),
                ),
                (
                    "db_lock_storage",
                    models.TextField(
                        blank=True,
                        help_text="Locks on this note.",
                        verbose_name="locks",
                    ),
                ),
                (
                    "db_status",
                    models.IntegerField(
                        choices=[
                            (1, "Recording"),
                            (2, "Paused"),
                            (3, "Draft"),
                            (4, "Completed"),
                            (5, "Published"),
                        ],
                        db_index=True,
                        default=1,
                        help_text="The current status of this scene.",
                    ),
                ),
                (
                    "db_reader_accounts",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_reader_accounts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="reader (account)",
                    ),
                ),
                (
                    "db_reader_objects",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_reader_objects",
                        to="objects.objectdb",
                        verbose_name="reader (object)",
                    ),
                ),
                (
                    "db_tags",
                    models.ManyToManyField(
                        blank=True, help_text="Tags on this note.", to="typeclasses.tag"
                    ),
                ),
                (
                    "db_writer_accounts",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_writer_accounts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="writer (account)",
                    ),
                ),
                (
                    "db_writer_objects",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_writer_objects",
                        to="objects.objectdb",
                        verbose_name="writer (object)",
                    ),
                ),
            ],
            options={
                "verbose_name": "Scene",
                "verbose_name_plural": "Scenes",
            },
        ),
        migrations.CreateModel(
            name="Report",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("db_title", models.TextField(blank=True, verbose_name="title")),
                ("db_content", models.TextField(blank=True, verbose_name="content")),
                (
                    "db_date_created",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="date created"
                    ),
                ),
                (
                    "db_lock_storage",
                    models.TextField(
                        blank=True,
                        help_text="Locks on this note.",
                        verbose_name="locks",
                    ),
                ),
                ("db_kind", models.CharField(blank=True, db_index=True, max_length=30)),
                (
                    "db_open",
                    models.BooleanField(
                        default=True,
                        help_text="True if this report is open (pending action).",
                    ),
                ),
                (
                    "db_reader_accounts",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_reader_accounts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="reader (account)",
                    ),
                ),
                (
                    "db_reader_objects",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_reader_objects",
                        to="objects.objectdb",
                        verbose_name="reader (object)",
                    ),
                ),
                (
                    "db_subject",
                    models.ForeignKey(
                        blank=True,
                        help_text="The subject of this report.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_subjects",
                        to="objects.objectdb",
                    ),
                ),
                (
                    "db_tags",
                    models.ManyToManyField(
                        blank=True, help_text="Tags on this note.", to="typeclasses.tag"
                    ),
                ),
                (
                    "db_writer_accounts",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_writer_accounts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="writer (account)",
                    ),
                ),
                (
                    "db_writer_objects",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_writer_objects",
                        to="objects.objectdb",
                        verbose_name="writer (object)",
                    ),
                ),
            ],
            options={
                "verbose_name": "Report",
                "verbose_name_plural": "Reports",
            },
        ),
        migrations.CreateModel(
            name="Article",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("db_title", models.TextField(blank=True, verbose_name="title")),
                ("db_content", models.TextField(blank=True, verbose_name="content")),
                (
                    "db_date_created",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="date created"
                    ),
                ),
                (
                    "db_lock_storage",
                    models.TextField(
                        blank=True,
                        help_text="Locks on this note.",
                        verbose_name="locks",
                    ),
                ),
                (
                    "db_category",
                    models.CharField(blank=True, db_index=True, max_length=30),
                ),
                (
                    "db_reader_accounts",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_reader_accounts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="reader (account)",
                    ),
                ),
                (
                    "db_reader_objects",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_reader_objects",
                        to="objects.objectdb",
                        verbose_name="reader (object)",
                    ),
                ),
                (
                    "db_tags",
                    models.ManyToManyField(
                        blank=True, help_text="Tags on this note.", to="typeclasses.tag"
                    ),
                ),
                (
                    "db_writer_accounts",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_writer_accounts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="writer (account)",
                    ),
                ),
                (
                    "db_writer_objects",
                    models.ManyToManyField(
                        blank=True,
                        db_index=True,
                        related_name="%(class)s_writer_objects",
                        to="objects.objectdb",
                        verbose_name="writer (object)",
                    ),
                ),
            ],
            options={
                "verbose_name": "Article",
                "verbose_name_plural": "Articles",
            },
        ),
    ]
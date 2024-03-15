from django.db import migrations, models

can_use_postgres_fields = False

# Dummy fields
chapter_numbers_field = models.Field()

try:
    from django.contrib.postgres.fields import ArrayField

    chapter_numbers_field = ArrayField(
        base_field=models.PositiveSmallIntegerField(), default=list, size=None
    )
    can_use_postgres_fields = True
except ImportError:
    # We can't use ArrayField if psycopg2 is not installed - issue #1125
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_alter_author_birthday"),
    ]

    operations = []

    pg_only_operations = [
        migrations.CreateModel(
            name="BookWithChapterNumbers",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Book name")),
                ("chapter_numbers", chapter_numbers_field),
            ],
        ),
    ]

    def apply(self, project_state, schema_editor, collect_sql=False):
        if can_use_postgres_fields and schema_editor.connection.vendor.startswith(
            "postgres"
        ):
            self.operations = self.operations + self.pg_only_operations
        return super().apply(project_state, schema_editor, collect_sql)

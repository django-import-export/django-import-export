from __future__ import unicode_literals

from django import VERSION
from django.db import migrations, models
if VERSION >= (1, 8):
    from django.contrib.postgres.fields import ArrayField
    chapters_field = ArrayField(base_field=models.CharField(max_length=100), default=list, size=None)
else:
    chapters_field = models.Field()  # Dummy field


class PostgresOnlyCreateModel(migrations.CreateModel):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if VERSION >= (1, 8) and schema_editor.connection.vendor.startswith("postgres"):
            super(PostgresOnlyCreateModel, self).database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if VERSION >= (1, 8) and schema_editor.connection.vendor.startswith("postgres"):
            super(PostgresOnlyCreateModel, self).database_backwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_withfloatfield'),
    ]

    operations = [
        PostgresOnlyCreateModel(
            name='BookWithChapters',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Book name')),
                ('chapters', chapters_field)
            ],
        ),
    ]

from django.db import migrations, models

can_use_postgres_fields = False
chapters_field = models.Field()  # Dummy field

try:
    from django.contrib.postgres.fields import ArrayField, JSONField

    chapters_field = ArrayField(base_field=models.CharField(max_length=100), default=list, size=None)
    data_field = JSONField(null=True)
    can_use_postgres_fields = True
except ImportError:
    # We can't use ArrayField if psycopg2 is not installed
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_withfloatfield'),
    ]

    operations = []

    pg_only_operations = [
        migrations.CreateModel(
            name='BookWithChapters',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Book name')),
                ('chapters', chapters_field),
                ('data', data_field)
            ],
        ),
    ]

    def apply(self, project_state, schema_editor, collect_sql=False):
        if can_use_postgres_fields and schema_editor.connection.vendor.startswith("postgres"):
            self.operations = self.operations + self.pg_only_operations
        return super().apply(project_state, schema_editor, collect_sql)

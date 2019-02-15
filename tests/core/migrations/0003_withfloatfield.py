from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_book_published_time'),
    ]

    operations = [
        migrations.CreateModel(
            name='WithFloatField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('f', models.FloatField(blank=True, null=True)),
            ],
        ),
    ]

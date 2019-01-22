from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='published_time',
            field=models.TimeField(blank=True, null=True, verbose_name='Time published'),
        ),
    ]

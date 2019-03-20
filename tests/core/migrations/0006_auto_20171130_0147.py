from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_addparentchild'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='name',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]

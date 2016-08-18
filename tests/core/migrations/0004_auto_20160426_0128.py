# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-26 01:28
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_withfloatfield'),
    ]

    operations = [
        migrations.CreateModel(
            name='ISBN',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='ISBN code')),
            ],
        ),
        migrations.AddField(
            model_name='book',
            name='isbn',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.ISBN', to_field='code'),
        ),
    ]

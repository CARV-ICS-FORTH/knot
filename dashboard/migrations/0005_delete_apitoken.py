# Generated by Django 3.2.10 on 2022-04-27 12:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_message'),
    ]

    operations = [
        migrations.DeleteModel(
            name='APIToken',
        ),
    ]

# Generated by Django 2.0.1 on 2018-03-07 23:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('madmex', '0024_auto_20180307_2148'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='predictobject',
            name='regions',
        ),
        migrations.RemoveField(
            model_name='trainobject',
            name='regions',
        ),
    ]

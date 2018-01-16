# Generated by Django 2.0 on 2018-01-16 22:55

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('madmex', '0005_order_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='added',
            field=models.DateField(default=datetime.datetime.now),
        ),
        migrations.AddField(
            model_name='footprint',
            name='added',
            field=models.DateField(default=datetime.datetime.now),
        ),
        migrations.AddField(
            model_name='order',
            name='added',
            field=models.DateField(default=datetime.datetime.now),
        ),
        migrations.AddField(
            model_name='region',
            name='added',
            field=models.DateField(default=datetime.datetime.now),
        ),
    ]

# Generated by Django 2.0.6 on 2018-06-13 23:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('madmex', '0040_validationresults'),
    ]

    operations = [
        migrations.AlterField(
            model_name='validationresults',
            name='comment',
            field=models.CharField(default='', max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='validationresults',
            name='region',
            field=models.CharField(default='', max_length=100, null=True),
        ),
    ]

# Generated by Django 2.1.5 on 2019-03-08 22:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('madmex', '0052_validobject_filename'),
    ]

    operations = [
        migrations.AlterField(
            model_name='validationresults',
            name='classification',
            field=models.CharField(default='', max_length=200),
        ),
        migrations.AlterField(
            model_name='validationresults',
            name='validation',
            field=models.CharField(default='', max_length=200),
        ),
    ]
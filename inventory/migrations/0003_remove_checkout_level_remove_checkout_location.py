# Generated by Django 4.0.6 on 2024-08-12 16:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_checkedoutby_checkout'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='checkout',
            name='level',
        ),
        migrations.RemoveField(
            model_name='checkout',
            name='location',
        ),
    ]

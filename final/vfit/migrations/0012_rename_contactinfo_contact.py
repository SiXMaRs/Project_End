# Generated by Django 5.1.4 on 2025-02-03 15:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vfit', '0011_contactinfo'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ContactInfo',
            new_name='Contact',
        ),
    ]

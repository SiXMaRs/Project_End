# Generated by Django 5.1.4 on 2024-12-15 15:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vfit', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='buy_record',
            old_name='product',
            new_name='product_id',
        ),
        migrations.RenameField(
            model_name='buy_record',
            old_name='user',
            new_name='user_id',
        ),
    ]

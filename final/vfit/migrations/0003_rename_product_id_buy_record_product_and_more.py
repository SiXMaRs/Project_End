# Generated by Django 5.1.4 on 2024-12-15 15:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vfit', '0002_rename_product_buy_record_product_id_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='buy_record',
            old_name='product_id',
            new_name='product',
        ),
        migrations.RenameField(
            model_name='buy_record',
            old_name='user_id',
            new_name='user',
        ),
    ]

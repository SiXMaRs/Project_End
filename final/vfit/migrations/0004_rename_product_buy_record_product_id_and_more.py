# Generated by Django 5.1.4 on 2024-12-15 16:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vfit', '0003_rename_product_id_buy_record_product_and_more'),
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
        migrations.AlterField(
            model_name='buy_record',
            name='total_price',
            field=models.FloatField(),
        ),
    ]

# Generated by Django 5.1.4 on 2025-02-03 15:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vfit', '0010_alter_rentalrecord_status_report'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('facebook', models.CharField(max_length=255)),
                ('instagram', models.CharField(max_length=255)),
                ('line', models.CharField(max_length=255)),
                ('phone', models.CharField(max_length=20)),
                ('address', models.TextField()),
            ],
        ),
    ]

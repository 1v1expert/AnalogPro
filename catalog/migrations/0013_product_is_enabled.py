# Generated by Django 2.1.5 on 2019-11-28 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0012_manufacturer_is_tried'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_enabled',
            field=models.BooleanField(default=False, verbose_name='Поисковый'),
        ),
    ]

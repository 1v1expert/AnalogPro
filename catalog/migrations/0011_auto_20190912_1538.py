# Generated by Django 2.1.5 on 2019-09-12 12:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0010_product_formalized_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_base',
            field=models.BooleanField(default=False, verbose_name='Базовый'),
        ),
        migrations.AlterField(
            model_name='product',
            name='formalized_title',
            field=models.CharField(max_length=255, null=True, verbose_name='Формализованное наименование'),
        ),
    ]

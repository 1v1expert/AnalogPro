# Generated by Django 2.2.10 on 2020-09-11 18:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0024_attribute_weight'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='product',
            options={'verbose_name': 'Товар', 'verbose_name_plural': 'Товары'},
        ),
        migrations.AlterField(
            model_name='product',
            name='priority',
            field=models.PositiveSmallIntegerField(blank=True, default=0, null=True, verbose_name='Приоритет'),
        ),
    ]

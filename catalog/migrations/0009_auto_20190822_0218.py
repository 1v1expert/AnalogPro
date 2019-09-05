# Generated by Django 2.1.5 on 2019-08-21 23:18

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0008_auto_20190818_1645'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='raw',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Голые данные'),
        ),
        migrations.AlterField(
            model_name='datafile',
            name='type',
            field=models.CharField(blank=True, choices=[('import', 'Импорт базы'), ('search', 'Поиск'), ('result_search', 'Результат поиска'), ('export', 'Экспорт данных')], default='import', max_length=13, verbose_name='Тип файла'),
        ),
    ]
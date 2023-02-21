# Generated by Django 4.0.2 on 2022-02-23 21:16

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_alter_product_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(1)]),
        ),
    ]

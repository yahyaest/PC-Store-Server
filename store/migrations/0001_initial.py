# Generated by Django 4.0.2 on 2022-02-20 18:12

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import store.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['title'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.JSONField(default=store.models.defaultJsonField)),
                ('price', models.CharField(max_length=255)),
                ('inventory', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('slug', models.SlugField()),
                ('last_update', models.DateTimeField(auto_now=True)),
                ('images', models.JSONField(default=store.models.defaultJsonField)),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='store.collection')),
            ],
            options={
                'ordering': ['title'],
            },
        ),
        migrations.AddField(
            model_name='collection',
            name='featured_product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='store.product'),
        ),
    ]

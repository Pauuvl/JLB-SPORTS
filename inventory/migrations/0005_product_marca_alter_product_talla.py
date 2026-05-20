# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_remove_product_brand_remove_product_color_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='marca',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='product',
            name='talla',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]

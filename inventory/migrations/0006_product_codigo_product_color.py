from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_product_marca_alter_product_talla'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='codigo',
            field=models.CharField(blank=True, default='', max_length=50, unique=True, verbose_name='Código'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='color',
            field=models.CharField(blank=True, default='', help_text='Colores disponibles separados por coma. Ej: Rojo, Azul, Negro', max_length=100, verbose_name='Color(es)'),
        ),
    ]

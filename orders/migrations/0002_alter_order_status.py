from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0001_initial'),
    ]
    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending',   'Pendiente'),
                    ('confirmed', 'Confirmado'),
                    ('converted', 'Convertido a Venta'),
                    ('cancelled', 'Cancelado'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]

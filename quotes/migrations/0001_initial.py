from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('clients', '0001_initial'),
        ('inventory', '0005_product_marca_alter_product_talla'),
    ]
    operations = [
        migrations.CreateModel(
            name='Quote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_name', models.CharField(blank=True, max_length=200)),
                ('status', models.CharField(choices=[('draft','Borrador'),('sent','Enviada'),('accepted','Aceptada'),('rejected','Rechazada')], default='draft', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('valid_days', models.PositiveIntegerField(default=15)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='quotes', to='clients.client')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='QuoteItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=300)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('quote', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='quotes.quote')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='inventory.product')),
            ],
        ),
    ]

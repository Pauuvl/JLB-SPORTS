from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='saleitem',
            name='color_vendido',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Color vendido'),
        ),
    ]

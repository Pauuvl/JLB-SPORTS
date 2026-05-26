from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Sum
from decimal import Decimal
from .models import Sale, SaleItem
from inventory.models import Product
from clients.models import Client


def _fmt_pesos(value):
    try:
        val = int(Decimal(str(value)))
        return f"${val:,}".replace(",", ".")
    except Exception:
        return f"${value}"


@login_required
def sale_list(request):
    sales = Sale.objects.select_related('client').prefetch_related('items__product').all()
    total_completadas = Sale.objects.filter(status='completed').aggregate(
        t=Sum('total_amount'))['t'] or 0
    context = {
        'sales': sales,
        'total_completadas': total_completadas,
        'active_page': 'sales',
    }
    return render(request, 'sales/sale_list.html', context)


@login_required
def sale_create(request):
    products = Product.objects.filter(stock_quantity__gt=0).select_related('category')
    clients = Client.objects.all()

    if request.method == 'POST':
        client_id = request.POST.get('client') or None
        notes = request.POST.get('notes', '')
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        colores = request.POST.getlist('color_vendido[]')

        if not product_ids:
            messages.error(request, 'Debe agregar al menos un producto a la venta.')
            return render(request, 'sales/sale_form.html', {
                'products': products, 'clients': clients, 'active_page': 'sales'
            })

        client = Client.objects.get(pk=client_id) if client_id else None
        price_multiplier = client.price_multiplier if client else 1.0

        try:
            with transaction.atomic():
                sale = Sale.objects.create(
                    client=client, notes=notes,
                    discount_applied=client.discount_percent if client else 0,
                )

                for i, (pid, qty) in enumerate(zip(product_ids, quantities)):
                    product = Product.objects.select_for_update().get(pk=pid)
                    qty = int(qty)
                    color = colores[i] if i < len(colores) else ''

                    if product.stock_quantity < qty:
                        raise ValueError(
                            f'Stock insuficiente para "{product.name}". '
                            f'Disponible: {product.stock_quantity}, Solicitado: {qty}'
                        )

                    unit_price = Decimal(str(product.sale_price)) * Decimal(str(price_multiplier))
                    SaleItem.objects.create(
                        sale=sale, product=product,
                        quantity=qty,
                        unit_price=unit_price.quantize(Decimal('1')),
                        color_vendido=color,
                    )

                    product.stock_quantity -= qty
                    product.save()

                sale.calculate_total()
                total_fmt = _fmt_pesos(sale.total_amount)
                messages.success(
                    request,
                    f'✅ Venta #{sale.pk} registrada exitosamente. Total: {total_fmt}'
                )
                return redirect('sale_detail', pk=sale.pk)

        except ValueError as e:
            messages.error(request, str(e))
        except Product.DoesNotExist:
            messages.error(request, 'Uno de los productos seleccionados no fue encontrado.')

    return render(request, 'sales/sale_form.html', {
        'products': products, 'clients': clients, 'active_page': 'sales'
    })


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('client').prefetch_related('items__product'), pk=pk
    )
    return render(request, 'sales/sale_detail.html', {
        'sale': sale, 'active_page': 'sales'
    })


@login_required
def sale_cancel(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == 'POST':
        if sale.status == 'completed':
            with transaction.atomic():
                for item in sale.items.all():
                    item.product.stock_quantity += item.quantity
                    item.product.save()
                sale.status = 'cancelled'
                sale.save()
            messages.success(
                request,
                f'Venta #{sale.pk} anulada. Stock restaurado automáticamente.'
            )
        else:
            messages.warning(request, 'Esta venta ya fue anulada anteriormente.')
        return redirect('sale_list')
    return render(request, 'sales/sale_cancel_confirm.html', {
        'sale': sale, 'active_page': 'sales'
    })


@login_required
def get_product_price(request):
    product_id = request.GET.get('product_id')
    client_id = request.GET.get('client_id')
    try:
        product = Product.objects.get(pk=product_id)
        price = float(product.sale_price)
        if client_id:
            client = Client.objects.get(pk=client_id)
            price = price * client.price_multiplier

        return JsonResponse({
            'price': int(round(price)),
            'stock': product.stock_quantity,
            'name': product.name,
            'codigo': product.codigo,
            'colores': product.get_colores_lista(),
            'status': 'agotado' if product.stock_quantity == 0
                      else ('bajo' if product.is_low_stock else 'ok'),
        })
    except (Product.DoesNotExist, Client.DoesNotExist):
        return JsonResponse({'error': 'No encontrado'}, status=404)

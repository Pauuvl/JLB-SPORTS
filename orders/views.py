from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from .models import Order, OrderItem
from inventory.models import Product
from clients.models import Client
from sales.models import Sale, SaleItem


def order_list(request):
    orders = Order.objects.select_related('client').all()
    context = {'orders': orders, 'active_page': 'orders'}
    return render(request, 'orders/order_list.html', context)


def order_create(request):
    products = Product.objects.select_related('category').all()
    clients = Client.objects.all()

    if request.method == 'POST':
        client_id = request.POST.get('client') or None
        notes = request.POST.get('notes', '')
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')

        if not product_ids:
            messages.error(request, 'Debe agregar al menos un producto.')
            return render(request, 'orders/order_form.html', {
                'products': products, 'clients': clients, 'active_page': 'orders'
            })

        client = Client.objects.get(pk=client_id) if client_id else None
        price_multiplier = client.price_multiplier if client else 1.0

        order = Order.objects.create(client=client, notes=notes)

        for pid, qty in zip(product_ids, quantities):
            product = Product.objects.get(pk=pid)
            unit_price = Decimal(str(product.sale_price)) * Decimal(str(price_multiplier))
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=int(qty),
                unit_price=unit_price.quantize(Decimal('0.01')),
            )

        order.calculate_total()
        messages.success(request, f'Pedido #{order.pk} creado.')
        return redirect('order_list')

    return render(request, 'orders/order_form.html', {
        'products': products, 'clients': clients, 'active_page': 'orders'
    })


def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('client').prefetch_related('items__product'), pk=pk
    )
    return render(request, 'orders/order_detail.html', {'order': order, 'active_page': 'orders'})


def order_confirm(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        if order.status != 'pending':
            messages.warning(request, 'Este pedido ya fue procesado.')
            return redirect('order_detail', pk=pk)
        try:
            order.confirm()
            messages.success(request, f'Pedido #{order.pk} confirmado. Stock descontado.')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('order_detail', pk=pk)
    return render(request, 'orders/order_confirm.html', {'order': order, 'active_page': 'orders'})


def order_to_sale(request, pk):
    """Convierte un pedido confirmado en venta registrada (sin descontar stock de nuevo)."""
    order = get_object_or_404(
        Order.objects.select_related('client').prefetch_related('items__product'), pk=pk
    )
    if request.method == 'POST':
        if order.status != 'confirmed':
            messages.error(request, 'Solo los pedidos confirmados pueden convertirse en venta.')
            return redirect('order_detail', pk=pk)
        with transaction.atomic():
            sale = Sale.objects.create(
                client=order.client,
                notes=f'Generado desde Pedido #{order.pk}. {order.notes}'.strip(),
                discount_applied=order.client.discount_percent if order.client else 0,
                total_amount=order.total_amount,
            )
            for item in order.items.all():
                SaleItem.objects.create(
                    sale=sale,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
            # Marcar pedido como convertido
            order.status = 'converted'
            order.save()
        messages.success(request, f'✅ Venta #{sale.pk} registrada desde el Pedido #{order.pk}.')
        return redirect('sale_detail', pk=sale.pk)
    return render(request, 'orders/order_to_sale_confirm.html', {'order': order, 'active_page': 'orders'})


def order_delete(request, pk):
    """Elimina un pedido. Si estaba confirmado, restaura el stock."""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'), pk=pk
    )
    if request.method == 'POST':
        with transaction.atomic():
            if order.status == 'confirmed':
                for item in order.items.all():
                    item.product.stock_quantity += item.quantity
                    item.product.save()
            order.delete()
        messages.success(request, f'Pedido #{pk} eliminado.')
        return redirect('order_list')
    return render(request, 'orders/order_delete_confirm.html', {'order': order, 'active_page': 'orders'})


def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        if order.status == 'pending':
            order.status = 'cancelled'
            order.save()
            messages.success(request, f'Pedido #{order.pk} cancelado.')
        else:
            messages.warning(request, 'Solo los pedidos pendientes se pueden cancelar.')
        return redirect('order_list')
    return render(request, 'orders/order_cancel_confirm.html', {'order': order, 'active_page': 'orders'})

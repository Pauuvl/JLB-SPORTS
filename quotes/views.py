from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from decimal import Decimal
from .models import Quote, QuoteItem
from inventory.models import Product
from clients.models import Client


def quote_list(request):
    quotes = Quote.objects.select_related('client').all()
    context = {'quotes': quotes, 'active_page': 'quotes'}
    return render(request, 'quotes/quote_list.html', context)


def quote_create(request):
    products = Product.objects.select_related('category').all()
    clients  = Client.objects.all()

    if request.method == 'POST':
        client_id   = request.POST.get('client') or None
        client_name = request.POST.get('client_name', '').strip()
        notes       = request.POST.get('notes', '')
        valid_days  = request.POST.get('valid_days', 15)
        product_ids = request.POST.getlist('product_id[]')
        quantities  = request.POST.getlist('quantity[]')
        prices      = request.POST.getlist('unit_price[]')
        descs       = request.POST.getlist('description[]')

        if not product_ids:
            messages.error(request, 'Debe agregar al menos un producto.')
            return render(request, 'quotes/quote_form.html', {
                'products': products, 'clients': clients, 'active_page': 'quotes'
            })

        client = Client.objects.get(pk=client_id) if client_id else None

        quote = Quote.objects.create(
            client=client,
            client_name=client_name if not client else '',
            notes=notes,
            valid_days=valid_days,
        )

        for pid, qty, price, desc in zip(product_ids, quantities, prices, descs):
            product = Product.objects.get(pk=pid) if pid else None
            QuoteItem.objects.create(
                quote=quote,
                product=product,
                description=desc or (product.name if product else ''),
                quantity=int(qty),
                unit_price=Decimal(price),
            )

        quote.calculate_total()
        messages.success(request, f'Cotización #{quote.pk} creada.')
        return redirect('quote_detail', pk=quote.pk)

    return render(request, 'quotes/quote_form.html', {
        'products': products, 'clients': clients, 'active_page': 'quotes'
    })


def quote_detail(request, pk):
    quote = get_object_or_404(
        Quote.objects.select_related('client').prefetch_related('items__product'), pk=pk
    )
    return render(request, 'quotes/quote_detail.html', {'quote': quote, 'active_page': 'quotes'})


def quote_status(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['draft', 'sent', 'accepted', 'rejected']:
            quote.status = new_status
            quote.save()
            messages.success(request, f'Cotización #{quote.pk} marcada como {quote.get_status_display()}.')
        return redirect('quote_detail', pk=pk)


def quote_delete(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if request.method == 'POST':
        quote.delete()
        messages.success(request, f'Cotización #{pk} eliminada.')
        return redirect('quote_list')
    return render(request, 'quotes/quote_delete_confirm.html', {'quote': quote, 'active_page': 'quotes'})

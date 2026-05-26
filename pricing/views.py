from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from inventory.models import Product
from .models import PriceList, PriceListItem
from clients.models import Client


@login_required
def pricing_overview(request):
    products = Product.objects.select_related('category').all()
    price_lists = PriceList.objects.filter(is_active=True).prefetch_related('items__product')

    context = {
        'products': products,
        'price_lists': price_lists,
        'active_page': 'pricing',
    }
    return render(request, 'pricing/pricing_overview.html', context)


@login_required
def price_list_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        client_type = request.POST.get('client_type', '')
        description = request.POST.get('description', '')
        if name:
            PriceList.objects.create(name=name, client_type=client_type, description=description)
            messages.success(request, f'Price list "{name}" created.')
            return redirect('pricing_overview')
    return render(request, 'pricing/price_list_form.html', {
        'client_types': Client.CLIENT_TYPES, 'active_page': 'pricing'
    })


@login_required
def price_list_detail(request, pk):
    price_list = get_object_or_404(PriceList, pk=pk)
    items = price_list.items.select_related('product').all()
    products = Product.objects.all()
    return render(request, 'pricing/price_list_detail.html', {
        'price_list': price_list, 'items': items, 'products': products, 'active_page': 'pricing'
    })


@login_required
def add_price_list_item(request, pk):
    price_list = get_object_or_404(PriceList, pk=pk)
    if request.method == 'POST':
        product_id = request.POST.get('product')
        custom_price = request.POST.get('custom_price')
        if product_id and custom_price:
            PriceListItem.objects.update_or_create(
                price_list=price_list,
                product_id=product_id,
                defaults={'custom_price': custom_price}
            )
            messages.success(request, 'Price updated.')
    return redirect('price_list_detail', pk=pk)

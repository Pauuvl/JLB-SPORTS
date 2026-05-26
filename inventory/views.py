from django.contrib.auth.decorators import login_required
# inventory/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from decimal import Decimal

from .models import Product, Category
from sales.models import Sale, SaleItem
from clients.models import Client
from orders.models import Order


@login_required
def dashboard(request):

    total_products = Product.objects.count()

    out_of_stock = Product.objects.filter(
        stock_quantity=0
    ).count()

    low_stock_products = Product.objects.filter(
        stock_quantity__gt=0,
        stock_quantity__lte=F('min_stock')
    ).select_related('category')

    low_stock_count = low_stock_products.count()

    total_inventory_value = sum(
        product.stock_value
        for product in Product.objects.all()
    )

    recent_sales = Sale.objects.select_related(
        'client'
    ).order_by('-created_at')[:6]

    total_sales = Sale.objects.filter(
        status='completed'
    ).count()

    total_revenue = Sale.objects.filter(
        status='completed'
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')

    total_clients = Client.objects.count()

    pending_orders = Order.objects.filter(
        status='pending'
    ).count()

    top_products = SaleItem.objects.values(
        'product__name'
    ).annotate(
        total_vendido=Sum('quantity')
    ).order_by('-total_vendido')[:5]

    context = {
        'total_products': total_products,
        'out_of_stock': out_of_stock,
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_count,
        'total_inventory_value': total_inventory_value,
        'recent_sales': recent_sales,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'total_clients': total_clients,
        'pending_orders': pending_orders,
        'top_products': top_products,
        'active_page': 'dashboard',
    }

    return render(request, 'dashboard.html', context)


@login_required
def product_list(request):

    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    stock_filter = request.GET.get('stock', '')

    products = Product.objects.select_related('category').all()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(marca__icontains=query) |
            Q(talla__icontains=query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    if stock_filter == 'bajo':
        products = products.filter(
            stock_quantity__gt=0,
            stock_quantity__lte=F('min_stock')
        )
    elif stock_filter == 'agotado':
        products = products.filter(stock_quantity=0)
    elif stock_filter == 'ok':
        products = products.filter(stock_quantity__gt=F('min_stock'))

    categories = Category.objects.all()

    total_count = Product.objects.count()
    low_count = Product.objects.filter(
        stock_quantity__gt=0,
        stock_quantity__lte=F('min_stock')
    ).count()
    out_count = Product.objects.filter(stock_quantity=0).count()

    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'stock_filter': stock_filter,
        'total_count': total_count,
        'low_count': low_count,
        'out_count': out_count,
        'active_page': 'inventory',
    }

    return render(request, 'inventory/product_list.html', context)


@login_required
def product_create(request):

    categories = Category.objects.all()

    if request.method == 'POST':

        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category') or None
        marca = request.POST.get('marca', '').strip()
        talla = request.POST.get('talla', '').strip()
        cost_price = request.POST.get('cost_price')
        sale_price = request.POST.get('sale_price')
        stock_quantity = request.POST.get('stock_quantity')
        min_stock = request.POST.get('min_stock', 5)
        description = request.POST.get('description', '')

        if not all([name, cost_price, sale_price, stock_quantity]):
            messages.error(
                request,
                'Por favor complete todos los campos requeridos.'
            )
        else:
            Product.objects.create(
                name=name,
                category_id=category_id,
                marca=marca,
                talla=talla,
                cost_price=cost_price,
                sale_price=sale_price,
                stock_quantity=stock_quantity,
                min_stock=min_stock,
                description=description,
            )
            messages.success(request, f'Producto "{name}" creado exitosamente.')
            return redirect('product_list')

    return render(
        request,
        'inventory/product_form.html',
        {
            'categories': categories,
            'active_page': 'inventory',
        }
    )


@login_required
def product_edit(request, pk):

    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all()

    if request.method == 'POST':

        product.name = request.POST.get('name', '').strip()
        product.category_id = request.POST.get('category') or None
        product.marca = request.POST.get('marca', '').strip()
        product.talla = request.POST.get('talla', '').strip()
        product.cost_price = request.POST.get('cost_price')
        product.sale_price = request.POST.get('sale_price')
        product.stock_quantity = request.POST.get('stock_quantity')
        product.min_stock = request.POST.get('min_stock', 5)
        product.description = request.POST.get('description', '')
        product.save()

        messages.success(request, f'Producto "{product.name}" actualizado.')
        return redirect('product_list')

    return render(
        request,
        'inventory/product_form.html',
        {
            'product': product,
            'categories': categories,
            'active_page': 'inventory',
        }
    )


@login_required
def product_delete(request, pk):

    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Producto "{name}" eliminado.')
        return redirect('product_list')

    return render(
        request,
        'inventory/product_confirm_delete.html',
        {'product': product, 'active_page': 'inventory'}
    )


@login_required
def category_list(request):

    categories = Category.objects.annotate(product_count=Count('products'))

    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Category.objects.create(name=name)
            messages.success(request, f'Categoría "{name}" creada.')
            return redirect('category_list')

    return render(
        request,
        'inventory/category_list.html',
        {'categories': categories, 'active_page': 'inventory'}
    )

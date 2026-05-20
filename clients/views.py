from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Sum, Q
from .models import Client


def client_list(request):
    query = request.GET.get('q', '')
    client_type = request.GET.get('type', '')
    clients = Client.objects.all()

    if query:
        clients = clients.filter(Q(name__icontains=query) | Q(email__icontains=query))
    if client_type:
        clients = clients.filter(client_type=client_type)

    context = {
        'clients': clients,
        'query': query,
        'selected_type': client_type,
        'client_types': Client.CLIENT_TYPES,
        'active_page': 'clients',
    }
    return render(request, 'clients/client_list.html', context)


def client_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        client_type = request.POST.get('client_type', 'regular')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        discount_percent = request.POST.get('discount_percent', 0)
        notes = request.POST.get('notes', '')

        if not name:
            messages.error(request, 'Client name is required.')
        else:
            Client.objects.create(
                name=name, client_type=client_type, email=email,
                phone=phone, address=address, discount_percent=discount_percent, notes=notes
            )
            messages.success(request, f'Client "{name}" created successfully.')
            return redirect('client_list')

    return render(request, 'clients/client_form.html', {
        'client_types': Client.CLIENT_TYPES, 'active_page': 'clients'
    })


def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.name = request.POST.get('name')
        client.client_type = request.POST.get('client_type', 'regular')
        client.email = request.POST.get('email', '')
        client.phone = request.POST.get('phone', '')
        client.address = request.POST.get('address', '')
        client.discount_percent = request.POST.get('discount_percent', 0)
        client.notes = request.POST.get('notes', '')
        client.save()
        messages.success(request, f'Client "{client.name}" updated.')
        return redirect('client_list')

    return render(request, 'clients/client_form.html', {
        'client': client, 'client_types': Client.CLIENT_TYPES, 'active_page': 'clients'
    })


def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        name = client.name
        client.delete()
        messages.success(request, f'Client "{name}" deleted.')
        return redirect('client_list')
    return render(request, 'clients/client_confirm_delete.html', {'client': client, 'active_page': 'clients'})


def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    sales = client.sales.order_by('-created_at')[:10]
    return render(request, 'clients/client_detail.html', {
        'client': client, 'sales': sales, 'active_page': 'clients'
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Sum, Q
from .models import Client


@login_required
def client_list(request):
    query = request.GET.get('q', '')
    client_type = request.GET.get('type', '')
    clients = Client.objects.all()

    if query:
        clients = clients.filter(Q(name__icontains=query) | Q(email__icontains=query) | Q(cedula__icontains=query))
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


def _save_client_from_post(client, post):
    client.name = post.get('name', '').strip()
    client.cedula = post.get('cedula', '').strip()
    client.client_type = post.get('client_type', 'regular')
    client.email = post.get('email', '')
    client.phone = post.get('phone', '')
    client.municipio = post.get('municipio', '').strip()
    client.address = post.get('address', '')
    client.discount_percent = post.get('discount_percent') or 0
    client.notes = post.get('notes', '')
    return client


@login_required
def client_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'El nombre del cliente es requerido.')
        else:
            client = _save_client_from_post(Client(), request.POST)
            client.save()
            messages.success(request, f'Cliente "{name}" registrado exitosamente.')
            return redirect('client_list')
    return render(request, 'clients/client_form.html', {
        'client_types': Client.CLIENT_TYPES, 'active_page': 'clients'
    })


@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client = _save_client_from_post(client, request.POST)
        client.save()
        messages.success(request, f'Cliente "{client.name}" actualizado.')
        return redirect('client_detail', pk=pk)
    return render(request, 'clients/client_form.html', {
        'client': client, 'client_types': Client.CLIENT_TYPES, 'active_page': 'clients'
    })


@login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        name = client.name
        client.delete()
        messages.success(request, f'Cliente "{name}" eliminado.')
        return redirect('client_list')
    return render(request, 'clients/client_confirm_delete.html', {'client': client, 'active_page': 'clients'})


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    sales = client.sales.order_by('-created_at')[:10]
    return render(request, 'clients/client_detail.html', {
        'client': client, 'sales': sales, 'active_page': 'clients'
    })

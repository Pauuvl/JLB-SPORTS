from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from decimal import Decimal
from .models import Quote, QuoteItem
from inventory.models import Product
from clients.models import Client
import json


def _build_products_json(products):
    data = []
    for p in products:
        data.append({
            'id': p.pk,
            'nombre': p.name,
            'codigo': p.codigo or '',
            'precio': float(p.sale_price),
            'stock': p.stock_quantity,
        })
    return json.dumps(data, ensure_ascii=False)


@login_required
def quote_list(request):
    quotes = Quote.objects.select_related('client').all()
    context = {'quotes': quotes, 'active_page': 'quotes'}
    return render(request, 'quotes/quote_list.html', context)


@login_required
def quote_create(request):
    products = Product.objects.select_related('category').all()
    clients = Client.objects.all()

    if request.method == 'POST':
        client_id = request.POST.get('client') or None
        client_name = request.POST.get('client_name', '').strip()
        notes = request.POST.get('notes', '')
        valid_days = request.POST.get('valid_days', 15)
        discount_pct = request.POST.get('discount_percent', '0') or '0'
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('unit_price[]')
        descs = request.POST.getlist('description[]')

        if not product_ids:
            messages.error(request, 'Debe agregar al menos un producto.')
            return render(request, 'quotes/quote_form.html', {
                'products': products, 'clients': clients,
                'products_json': _build_products_json(products), 'active_page': 'quotes'
            })

        try:
            discount = Decimal(str(discount_pct))
            if discount < 0 or discount > 100:
                discount = Decimal('0')
        except Exception:
            discount = Decimal('0')

        client = Client.objects.get(pk=client_id) if client_id else None

        quote = Quote.objects.create(
            client=client,
            client_name=client_name if not client else '',
            notes=notes,
            valid_days=valid_days,
            discount_applied=discount,
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
        'products': products, 'clients': clients,
        'products_json': _build_products_json(products), 'active_page': 'quotes'
    })


@login_required
def quote_detail(request, pk):
    quote = get_object_or_404(
        Quote.objects.select_related('client').prefetch_related('items__product'), pk=pk
    )
    return render(request, 'quotes/quote_detail.html', {'quote': quote, 'active_page': 'quotes'})


@login_required
def quote_status(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['draft', 'sent', 'accepted', 'rejected']:
            quote.status = new_status
            quote.save()
            messages.success(request, f'Cotización #{quote.pk} marcada como {quote.get_status_display()}.')
        return redirect('quote_detail', pk=pk)


@login_required
def quote_delete(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if request.method == 'POST':
        quote.delete()
        messages.success(request, f'Cotización #{pk} eliminada.')
        return redirect('quote_list')
    return render(request, 'quotes/quote_delete_confirm.html', {'quote': quote, 'active_page': 'quotes'})


@login_required
def quote_pdf(request, pk):
    quote = get_object_or_404(
        Quote.objects.select_related('client').prefetch_related('items__product'), pk=pk
    )
    pdf_bytes = generate_quote_pdf(quote)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="cotizacion_{quote.pk}.pdf"'
    return response


def generate_quote_pdf(quote):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    rojo = colors.HexColor('#DC2626')
    negro = colors.HexColor('#111111')
    gris = colors.HexColor('#6B7280')
    gris_fondo = colors.HexColor('#F3F4F6')
    azul = colors.HexColor('#1D4ED8')

    title_style = ParagraphStyle('title', fontSize=20, textColor=colors.white,
                                  fontName='Helvetica-Bold', alignment=TA_CENTER)
    sub_style = ParagraphStyle('sub', fontSize=9, textColor=colors.white,
                                fontName='Helvetica', alignment=TA_CENTER)
    normal_style = ParagraphStyle('normal', fontSize=9, textColor=gris, fontName='Helvetica')

    elements = []

    # Header
    header_data = [[
        Paragraph('<font color="white"><b>JLB SPORTS</b></font><br/><font size="8" color="#bfdbfe">Sistema de Gestión Comercial</font>', title_style),
        Paragraph(f'<font color="white"><b>COTIZACIÓN #{quote.pk}</b></font><br/><font size="8" color="#bfdbfe">{quote.created_at.strftime("%d/%m/%Y")} · Válida {quote.valid_days} días</font>', sub_style),
    ]]
    header_table = Table(header_data, colWidths=[11*cm, 6*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), azul),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING', (0, 0), (0, -1), 18),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 18),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))

    # Client info
    client = quote.client
    client_info = []
    display_name = client.name if client else (quote.client_name or 'Sin cliente')
    client_info.append(['Cliente:', display_name])
    if client:
        if client.cedula:
            client_info.append(['Cédula / NIT:', client.cedula])
        if client.phone:
            client_info.append(['Teléfono:', client.phone])
        if client.email:
            client_info.append(['Correo:', client.email])
        if client.municipio:
            client_info.append(['Municipio:', client.municipio])

    client_table = Table(client_info, colWidths=[4*cm, 13*cm])
    client_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 9),
        ('FONT', (1, 0), (1, -1), 'Helvetica', 9),
        ('TEXTCOLOR', (0, 0), (0, -1), negro),
        ('TEXTCOLOR', (1, 0), (1, -1), gris),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, -1), gris_fondo),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 0.4*cm))

    # Items
    items_data = [['Descripción', 'Cant.', 'Precio Unit.', 'Subtotal']]
    subtotal_sum = Decimal('0')
    for item in quote.items.all():
        subtotal_sum += item.subtotal
        items_data.append([
            item.description,
            str(item.quantity),
            f'${int(item.unit_price):,}'.replace(',', '.'),
            f'${int(item.subtotal):,}'.replace(',', '.'),
        ])

    items_table = Table(items_data, colWidths=[9.5*cm, 2*cm, 3.5*cm, 2*cm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), negro),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), negro),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gris_fondo]),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, azul),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.3*cm))

    # Totals
    totals_data = []
    totals_data.append(['Subtotal:', f'${int(subtotal_sum):,}'.replace(',', '.')])
    if quote.discount_applied:
        totals_data.append([f'Descuento ({quote.discount_applied}%):', f'-${int(subtotal_sum - quote.total_amount):,}'.replace(',', '.')])
    totals_data.append(['TOTAL:', f'${int(quote.total_amount):,}'.replace(',', '.')])

    totals_table = Table(totals_data, colWidths=[13.5*cm, 3.5*cm])
    totals_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -2), 'Helvetica', 9),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 13),
        ('TEXTCOLOR', (0, 0), (-1, -2), gris),
        ('TEXTCOLOR', (0, -1), (0, -1), negro),
        ('TEXTCOLOR', (-1, -1), (-1, -1), azul),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#EFF6FF')),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, azul),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
    ]))
    elements.append(totals_table)

    if quote.notes:
        elements.append(Spacer(1, 0.4*cm))
        elements.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#E5E7EB')))
        elements.append(Spacer(1, 0.2*cm))
        elements.append(Paragraph(f'<b>Observaciones:</b> {quote.notes}', normal_style))

    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=azul))
    elements.append(Spacer(1, 0.2*cm))
    footer_style = ParagraphStyle('footer', fontSize=7.5, textColor=gris, alignment=TA_CENTER)
    elements.append(Paragraph(
        f'Esta cotización es válida por {quote.valid_days} días a partir de su fecha de emisión · JLB Sports',
        footer_style
    ))

    doc.build(elements)
    return buffer.getvalue()

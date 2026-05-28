import json
import os
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum
from decimal import Decimal
from .models import Sale, SaleItem
from inventory.models import Product, ProductColorStock
from clients.models import Client


def _fmt_pesos(value):
    try:
        val = int(Decimal(str(value)))
        return f"${val:,}".replace(",", ".")
    except Exception:
        return f"${value}"


def _build_products_json(products):
    data = []
    for p in products:
        color_stocks = list(p.color_stocks.values('color', 'stock'))
        data.append({
            'id': p.pk,
            'nombre': p.name,
            'codigo': p.codigo or '',
            'precio': float(p.sale_price),
            'stock': p.stock_quantity,
            'colores': p.get_colores_lista(),
            'color_stocks': color_stocks,
        })
    return json.dumps(data, ensure_ascii=False)


@login_required
def sale_list(request):
    sales = Sale.objects.select_related('client').prefetch_related('items__product').all()
    total_completadas = Sale.objects.filter(status='completed').aggregate(t=Sum('total_amount'))['t'] or 0
    context = {'sales': sales, 'total_completadas': total_completadas, 'active_page': 'sales'}
    return render(request, 'sales/sale_list.html', context)


@login_required
def sale_create(request):
    products = Product.objects.select_related('category').prefetch_related('color_stocks').order_by('name')
    clients = Client.objects.all()

    if request.method == 'POST':
        client_id = request.POST.get('client') or None
        notes = request.POST.get('notes', '')
        discount_pct = request.POST.get('discount_percent', '0') or '0'
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        colores = request.POST.getlist('color_vendido[]')

        if not product_ids:
            messages.error(request, 'Debe agregar al menos un producto a la venta.')
            return render(request, 'sales/sale_form.html', {
                'products': products, 'clients': clients,
                'products_json': _build_products_json(products), 'active_page': 'sales',
            })

        client = Client.objects.get(pk=client_id) if client_id else None

        try:
            discount = Decimal(str(discount_pct))
            if discount < 0 or discount > 100:
                raise ValueError("El descuento debe estar entre 0% y 100%.")
        except Exception:
            discount = Decimal('0')

        try:
            with transaction.atomic():
                sale = Sale.objects.create(
                    client=client, notes=notes, discount_applied=discount,
                )

                for i, (pid, qty) in enumerate(zip(product_ids, quantities)):
                    product = Product.objects.select_for_update().get(pk=pid)
                    qty = int(qty)
                    color = colores[i] if i < len(colores) else ''

                    # Check general stock
                    if product.stock_quantity < qty:
                        raise ValueError(
                            f'Stock insuficiente para "{product.name}". '
                            f'Disponible: {product.stock_quantity}, Solicitado: {qty}'
                        )

                    # Check color stock if applicable
                    if color:
                        cs = ProductColorStock.objects.filter(product=product, color=color).first()
                        if cs and cs.stock < qty:
                            raise ValueError(
                                f'Stock de color "{color}" insuficiente para "{product.name}". '
                                f'Disponible: {cs.stock}, Solicitado: {qty}'
                            )

                    unit_price = Decimal(str(product.sale_price))
                    SaleItem.objects.create(
                        sale=sale, product=product,
                        quantity=qty,
                        unit_price=unit_price.quantize(Decimal('1')),
                        color_vendido=color,
                    )

                    # Deduct general stock
                    product.stock_quantity -= qty
                    product.save()

                    # Deduct color stock
                    if color:
                        ProductColorStock.objects.filter(product=product, color=color).update(
                            stock=models_F_expr(color, qty, product)
                        )

                sale.calculate_total()
                total_fmt = _fmt_pesos(sale.total_amount)
                messages.success(request, f'✅ Venta #{sale.pk} registrada. Total: {total_fmt}')
                return redirect('sale_detail', pk=sale.pk)

        except ValueError as e:
            messages.error(request, str(e))
        except Product.DoesNotExist:
            messages.error(request, 'Uno de los productos seleccionados no fue encontrado.')

    return render(request, 'sales/sale_form.html', {
        'products': products, 'clients': clients,
        'products_json': _build_products_json(products), 'active_page': 'sales',
    })


def models_F_expr(color, qty, product):
    """Helper to subtract qty from color stock using raw update."""
    from django.db.models import F
    cs = ProductColorStock.objects.filter(product=product, color=color).first()
    if cs:
        cs.stock = max(0, cs.stock - qty)
        cs.save()
    return cs.stock if cs else 0


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('client').prefetch_related('items__product'), pk=pk
    )
    return render(request, 'sales/sale_detail.html', {'sale': sale, 'active_page': 'sales'})


@login_required
def sale_cancel(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == 'POST':
        if sale.status == 'completed':
            with transaction.atomic():
                for item in sale.items.all():
                    item.product.stock_quantity += item.quantity
                    item.product.save()
                    # Restore color stock if applicable
                    if item.color_vendido:
                        cs = ProductColorStock.objects.filter(
                            product=item.product, color=item.color_vendido
                        ).first()
                        if cs:
                            cs.stock += item.quantity
                            cs.save()
                sale.status = 'cancelled'
                sale.save()
            messages.success(request, f'Venta #{sale.pk} anulada. Stock restaurado.')
        else:
            messages.warning(request, 'Esta venta ya fue anulada.')
        return redirect('sale_list')
    return render(request, 'sales/sale_cancel_confirm.html', {'sale': sale, 'active_page': 'sales'})


@login_required
def sale_pdf(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('client').prefetch_related('items__product'), pk=pk
    )
    pdf_bytes = generate_sale_pdf(sale)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="factura_{sale.pk}.pdf"'
    return response


def generate_sale_pdf(sale):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.pdfgen import canvas
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    rojo = colors.HexColor('#DC2626')
    negro = colors.HexColor('#111111')
    gris = colors.HexColor('#6B7280')
    gris_fondo = colors.HexColor('#F3F4F6')

    title_style = ParagraphStyle('title', fontSize=22, textColor=colors.white,
                                  fontName='Helvetica-Bold', alignment=TA_CENTER)
    sub_style = ParagraphStyle('sub', fontSize=9, textColor=colors.white,
                                fontName='Helvetica', alignment=TA_CENTER)
    heading_style = ParagraphStyle('heading', fontSize=11, textColor=negro,
                                    fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('normal', fontSize=9, textColor=gris, fontName='Helvetica')
    right_style = ParagraphStyle('right', fontSize=9, textColor=gris, fontName='Helvetica',
                                  alignment=TA_RIGHT)
    total_style = ParagraphStyle('total', fontSize=16, textColor=rojo,
                                  fontName='Helvetica-Bold', alignment=TA_RIGHT)

    elements = []

    # Header banner
    logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'imagenes', 'logo.png')

    header_data = [[
        Paragraph('<font color="white"><b>JLB SPORTS</b></font><br/><font size="8" color="#fecaca">Sistema de Gestión Comercial</font>', title_style),
        Paragraph(f'<font color="white"><b>FACTURA #{sale.pk}</b></font><br/><font size="8" color="#fecaca">{sale.created_at.strftime("%d/%m/%Y %H:%M")}</font>', sub_style),
    ]]
    header_table = Table(header_data, colWidths=[11*cm, 6*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), rojo),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING', (0, 0), (0, -1), 18),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 18),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))

    # Client info
    client = sale.client
    client_info = []
    if client:
        client_info.append(['Cliente:', client.name])
        if client.cedula:
            client_info.append(['Cédula / NIT:', client.cedula])
        if client.phone:
            client_info.append(['Teléfono:', client.phone])
        if client.email:
            client_info.append(['Correo:', client.email])
        if client.address:
            client_info.append(['Dirección:', client.address])
        if client.municipio:
            client_info.append(['Municipio:', client.municipio])
    else:
        client_info.append(['Cliente:', 'Venta Mostrador'])

    client_table = Table(client_info, colWidths=[4*cm, 13*cm])
    client_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 9),
        ('FONT', (1, 0), (1, -1), 'Helvetica', 9),
        ('TEXTCOLOR', (0, 0), (0, -1), negro),
        ('TEXTCOLOR', (1, 0), (1, -1), gris),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, -1), gris_fondo),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 0.4*cm))

    # Items table
    items_data = [['Código', 'Producto', 'Color', 'Cant.', 'Precio Unit.', 'Subtotal']]
    subtotal_sum = Decimal('0')
    for item in sale.items.all():
        subtotal_sum += item.subtotal
        items_data.append([
            item.product.codigo or '—',
            item.product.name,
            item.color_vendido or '—',
            str(item.quantity),
            f'${int(item.unit_price):,}'.replace(',', '.'),
            f'${int(item.subtotal):,}'.replace(',', '.'),
        ])

    items_table = Table(items_data, colWidths=[2.5*cm, 6*cm, 2.5*cm, 1.5*cm, 2.5*cm, 2*cm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), negro),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), negro),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gris_fondo]),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, rojo),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.3*cm))

    # Totals
    totals_data = []
    totals_data.append(['Subtotal:', f'${int(subtotal_sum):,}'.replace(',', '.')])
    if sale.discount_applied:
        totals_data.append([f'Descuento ({sale.discount_applied}%):', f'-${int(subtotal_sum - sale.total_amount):,}'.replace(',', '.')])
    totals_data.append(['TOTAL:', f'${int(sale.total_amount):,}'.replace(',', '.')])

    totals_table = Table(totals_data, colWidths=[13.5*cm, 3.5*cm])
    ts = [
        ('FONT', (0, 0), (-1, -2), 'Helvetica', 9),
        ('FONT', (-1, 0), (-1, -2), 'Helvetica', 9),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 13),
        ('TEXTCOLOR', (0, 0), (-1, -2), gris),
        ('TEXTCOLOR', (0, -1), (0, -1), negro),
        ('TEXTCOLOR', (-1, -1), (-1, -1), rojo),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FEF2F2')),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, rojo),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
    ]
    totals_table.setStyle(TableStyle(ts))
    elements.append(totals_table)

    # Notes
    if sale.notes:
        elements.append(Spacer(1, 0.4*cm))
        elements.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#E5E7EB')))
        elements.append(Spacer(1, 0.2*cm))
        elements.append(Paragraph(f'<b>Observaciones:</b> {sale.notes}', normal_style))

    # Footer
    elements.append(Spacer(1, 0.8*cm))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=rojo))
    elements.append(Spacer(1, 0.2*cm))
    footer_style = ParagraphStyle('footer', fontSize=7.5, textColor=gris, alignment=TA_CENTER)
    elements.append(Paragraph('JLB Sports — Sistema de Gestión Comercial · Gracias por su compra', footer_style))

    doc.build(elements)
    return buffer.getvalue()


@login_required
def get_product_price(request):
    product_id = request.GET.get('product_id')
    try:
        product = Product.objects.prefetch_related('color_stocks').get(pk=product_id)
        color_stocks = list(product.color_stocks.values('color', 'stock'))
        return JsonResponse({
            'price': int(round(float(product.sale_price))),
            'stock': product.stock_quantity,
            'name': product.name,
            'codigo': product.codigo,
            'colores': product.get_colores_lista(),
            'color_stocks': color_stocks,
            'status': 'agotado' if product.stock_quantity == 0
                      else ('bajo' if product.is_low_stock else 'ok'),
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'No encontrado'}, status=404)

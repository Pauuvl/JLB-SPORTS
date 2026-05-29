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

                    # ── Validar stock general ──────────────────────────
                    if product.stock_quantity < qty:
                        raise ValueError(
                            f'Stock insuficiente para "{product.name}". '
                            f'Disponible: {product.stock_quantity}, Solicitado: {qty}'
                        )

                    # ── Validar y obtener stock por color ──────────────
                    cs = None
                    if color:
                        cs = ProductColorStock.objects.select_for_update().filter(
                            product=product, color=color
                        ).first()
                        if cs is None:
                            raise ValueError(
                                f'El color "{color}" no está registrado para "{product.name}".'
                            )
                        if cs.stock < qty:
                            raise ValueError(
                                f'Stock del color "{color}" insuficiente para "{product.name}". '
                                f'Disponible: {cs.stock}, Solicitado: {qty}'
                            )

                    unit_price = Decimal(str(product.sale_price))
                    SaleItem.objects.create(
                        sale=sale, product=product,
                        quantity=qty,
                        unit_price=unit_price.quantize(Decimal('1')),
                        color_vendido=color,
                    )

                    # ── Descontar stock general ────────────────────────
                    product.stock_quantity -= qty
                    product.save()

                    # ── Descontar stock por color ──────────────────────
                    if cs is not None:
                        cs.stock -= qty
                        cs.save()

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
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable, Image,
                                    KeepTogether)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=1.8*cm, leftMargin=1.8*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm)

    # ── Paleta ────────────────────────────────────────────────────────────────
    ROJO       = colors.HexColor('#DC2626')
    ROJO_OSC   = colors.HexColor('#991B1B')
    NEGRO      = colors.HexColor('#111111')
    GRIS       = colors.HexColor('#6B7280')
    GRIS_FONDO = colors.HexColor('#F3F4F6')
    GRIS_BORDE = colors.HexColor('#E5E7EB')
    ROJO_LIGHT = colors.HexColor('#FEF2F2')
    BLANCO     = colors.white

    # ── Estilos ───────────────────────────────────────────────────────────────
    s_sub    = ParagraphStyle('sub',    fontSize=8,  textColor=BLANCO,  fontName='Helvetica',      alignment=TA_RIGHT)
    s_normal = ParagraphStyle('norm',   fontSize=9,  textColor=GRIS,    fontName='Helvetica')
    s_bold   = ParagraphStyle('bold',   fontSize=9,  textColor=NEGRO,   fontName='Helvetica-Bold')
    s_footer = ParagraphStyle('footer', fontSize=7,  textColor=GRIS,    fontName='Helvetica',      alignment=TA_CENTER)
    s_label  = ParagraphStyle('label',  fontSize=7,  textColor=GRIS,    fontName='Helvetica-Bold', spaceAfter=1)
    s_value  = ParagraphStyle('value',  fontSize=9,  textColor=NEGRO,   fontName='Helvetica')
    s_total  = ParagraphStyle('total',  fontSize=15, textColor=ROJO,    fontName='Helvetica-Bold', alignment=TA_RIGHT)

    W = 17.4 * cm  # ancho útil (A4 - márgenes)
    elements = []

    # ═══════════════════════════════════════════════════════════════════════════
    # HEADER: logo izq | info factura der
    # ═══════════════════════════════════════════════════════════════════════════
    logo_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'static', 'imagenes', 'logo_blanco.png')
    )
    if os.path.exists(logo_path):
        logo_cell = Image(logo_path, width=5.5*cm, height=1.7*cm)
    else:
        logo_cell = Paragraph('<font color="white" size="16"><b>JLB SPORTS</b></font>', s_sub)

    estado_color = '#16a34a' if sale.status == 'completed' else '#dc2626'
    estado_txt   = sale.get_status_display() if hasattr(sale, 'get_status_display') else sale.status.upper()

    info_cell = Paragraph(
        f'<font size="14" color="white"><b>FACTURA #{sale.pk}</b></font><br/>'
        f'<font size="8" color="#fca5a5">{sale.created_at.strftime("%d/%m/%Y  %H:%M")}  ·  '
        f'<b>{estado_txt}</b></font>',
        s_sub
    )

    hdr = Table([[logo_cell, info_cell]], colWidths=[10*cm, 7.4*cm])
    hdr.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), NEGRO),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING',   (0, 0), (0,  -1), 16),
        ('RIGHTPADDING',  (-1, 0), (-1, -1), 16),
        ('LINEBELOW',     (0, 0), (-1, -1), 3, ROJO),
    ]))
    elements.append(hdr)
    elements.append(Spacer(1, 0.45*cm))

    # ═══════════════════════════════════════════════════════════════════════════
    # INFO BLOQUE: datos cliente + datos venta lado a lado
    # ═══════════════════════════════════════════════════════════════════════════
    client = sale.client

    def info_block(label, value):
        return [Paragraph(label.upper(), s_label), Paragraph(str(value) if value else '—', s_value)]

    # columna izquierda: cliente
    if client:
        cli_rows = [
            info_block('Cliente', client.name),
            info_block('Cédula / NIT', client.cedula or None),
            info_block('Teléfono', client.phone or None),
            info_block('Municipio', client.municipio or None),
        ]
        cli_rows = [r for r in cli_rows if r[1].text != '—' or r[0].text == 'CLIENTE']
    else:
        cli_rows = [info_block('Cliente', 'Venta Mostrador')]

    # columna derecha: datos venta
    venta_rows = [
        info_block('Fecha', sale.created_at.strftime('%d/%m/%Y')),
        info_block('Hora', sale.created_at.strftime('%H:%M')),
        info_block('Vendedor', sale.created_by.get_full_name() if hasattr(sale, 'created_by') and sale.created_by else '—'),
    ]

    # Renderizar como tabla de 2 columnas
    def flatten_pairs(rows):
        result = []
        for pair in rows:
            result.append(pair)
        return result

    cli_flat  = flatten_pairs(cli_rows)
    venta_flat = flatten_pairs(venta_rows)

    # Igualar filas
    while len(cli_flat) < len(venta_flat):
        cli_flat.append([Paragraph('', s_label), Paragraph('', s_value)])
    while len(venta_flat) < len(cli_flat):
        venta_flat.append([Paragraph('', s_label), Paragraph('', s_value)])

    info_rows = [[cli_flat[i][0], cli_flat[i][1], venta_flat[i][0], venta_flat[i][1]]
                 for i in range(len(cli_flat))]

    info_tbl = Table(info_rows, colWidths=[2.8*cm, 6*cm, 2.8*cm, 5.8*cm])
    info_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GRIS_FONDO),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('LINEAFTER',     (1, 0), (1, -1), 0.5, GRIS_BORDE),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(info_tbl)
    elements.append(Spacer(1, 0.45*cm))

    # ═══════════════════════════════════════════════════════════════════════════
    # TABLA DE PRODUCTOS
    # ═══════════════════════════════════════════════════════════════════════════
    col_headers = ['#', 'Código', 'Producto', 'Color', 'Cant.', 'Precio Unit.', 'Subtotal']
    rows = [col_headers]
    subtotal_sum = Decimal('0')

    for i, item in enumerate(sale.items.all(), 1):
        subtotal_sum += item.subtotal
        rows.append([
            str(i),
            item.product.codigo or '—',
            item.product.name,
            item.color_vendido or '—',
            str(item.quantity),
            f'${int(item.unit_price):,}'.replace(',', '.'),
            f'${int(item.subtotal):,}'.replace(',', '.'),
        ])

    col_w = [0.7*cm, 2.2*cm, 5.8*cm, 2.3*cm, 1.3*cm, 2.6*cm, 2.5*cm]
    prod_tbl = Table(rows, colWidths=col_w, repeatRows=1)
    prod_tbl.setStyle(TableStyle([
        # encabezado
        ('BACKGROUND',    (0, 0), (-1, 0), NEGRO),
        ('TEXTCOLOR',     (0, 0), (-1, 0), BLANCO),
        ('FONT',          (0, 0), (-1, 0), 'Helvetica-Bold', 8),
        ('LINEBELOW',     (0, 0), (-1, 0), 2, ROJO),
        # filas
        ('FONT',          (0, 1), (-1, -1), 'Helvetica', 8),
        ('TEXTCOLOR',     (0, 1), (-1, -1), NEGRO),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [BLANCO, GRIS_FONDO]),
        # alineaciones
        ('ALIGN',         (0, 0), (0, -1), 'CENTER'),
        ('ALIGN',         (4, 0), (-1, -1), 'RIGHT'),
        # padding
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING',   (0, 0), (-1, -1), 7),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 7),
        # borde inferior total
        ('LINEBELOW',     (0, -1), (-1, -1), 0.5, GRIS_BORDE),
    ]))
    elements.append(prod_tbl)
    elements.append(Spacer(1, 0.3*cm))

    # ═══════════════════════════════════════════════════════════════════════════
    # TOTALES
    # ═══════════════════════════════════════════════════════════════════════════
    totals = []
    totals.append(['Subtotal:', f'${int(subtotal_sum):,}'.replace(',', '.')])
    if sale.discount_applied:
        desc_monto = subtotal_sum - sale.total_amount
        totals.append([f'Descuento ({sale.discount_applied}%):', f'-${int(desc_monto):,}'.replace(',', '.')])
    totals.append(['TOTAL A PAGAR:', f'${int(sale.total_amount):,}'.replace(',', '.')])

    tot_tbl = Table(totals, colWidths=[13.9*cm, 3.5*cm])
    tot_tbl.setStyle(TableStyle([
        ('FONT',          (0, 0), (-1, -2), 'Helvetica', 9),
        ('FONT',          (0, -1), (-1, -1), 'Helvetica-Bold', 13),
        ('TEXTCOLOR',     (0, 0), (-1, -2), GRIS),
        ('TEXTCOLOR',     (0, -1), (0, -1), NEGRO),
        ('TEXTCOLOR',     (-1, -1), (-1, -1), ROJO),
        ('ALIGN',         (0, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND',    (0, -1), (-1, -1), ROJO_LIGHT),
        ('LINEABOVE',     (0, -1), (-1, -1), 2, ROJO),
        ('RIGHTPADDING',  (-1, 0), (-1, -1), 0),
    ]))
    elements.append(KeepTogether([tot_tbl]))

    # ═══════════════════════════════════════════════════════════════════════════
    # OBSERVACIONES
    # ═══════════════════════════════════════════════════════════════════════════
    if sale.notes:
        elements.append(Spacer(1, 0.4*cm))
        elements.append(HRFlowable(width='100%', thickness=0.5, color=GRIS_BORDE))
        elements.append(Spacer(1, 0.2*cm))
        elements.append(Paragraph(f'<b>Observaciones:</b> {sale.notes}', s_normal))

    # ═══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════════════════
    elements.append(Spacer(1, 0.7*cm))
    elements.append(HRFlowable(width='100%', thickness=1, color=ROJO))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        'JLB Sports  ·  Sistema de Gestión Comercial  ·  ¡Gracias por su compra!',
        s_footer
    ))

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

"""Genera docs/05_ECONOMIA_UNITARIA.xlsx · V2.1 · mercado EE. UU. (USD).

Corrige la revisión externa V2:
- «Test de precio» descuenta TODAS las partidas variables (devoluciones esperadas,
  contenido/colaboradores, reserva, atención, envío, aranceles…) y usa la comisión
  real cuando existe (antes omitía G16/G17 y usaba siempre la comisión global).
- Sin IVA español: en EE. UU. el precio se anuncia sin impuestos y el sales tax se
  cobra en el checkout y se ingresa al estado (no es ingreso del vendedor).
- Ningún coste, precio ni umbral real inventado: las celdas de datos están vacías y la
  hoja muestra «DATOS INCOMPLETOS» hasta que el titular las rellene. Los precios de la
  hoja «Test de precio» son PUNTOS DE PRUEBA editables, no precios decididos.
- Sin LTV ni suscripción: el producto es reutilizable (margen del primer pedido).
Uso: python3 tools/finance/build_economia_us.py [salida.xlsx]
"""
import sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.formatting.rule import FormulaRule

OUT = sys.argv[1] if len(sys.argv) > 1 else 'docs/05_ECONOMIA_UNITARIA.xlsx'
F = 'Arial'
BLUE = Font(name=F, color='0000FF'); BLACK = Font(name=F); BOLD = Font(name=F, bold=True)
GREEN = Font(name=F, color='008000'); H1 = Font(name=F, bold=True, size=14); HDR = Font(name=F, bold=True, color='FFFFFF')
YEL = PatternFill('solid', fgColor='FFFF00'); NIGHT = PatternFill('solid', fgColor='172B37'); REDF = PatternFill('solid', fgColor='F4CCCC')
USD = '$#,##0.00;($#,##0.00);-'; PCT = '0.0%'
INC = 'DATOS INCOMPLETOS'

wb = Workbook()


def header(ws, row, titles):
    for j, t in enumerate(titles, 1):
        c = ws.cell(row, j, t); c.font = HDR; c.fill = NIGHT; c.alignment = Alignment(wrap_text=True, vertical='center')
    ws.row_dimensions[row].height = 34


def inp(ws, r, c, v, fmt=USD):
    cell = ws.cell(r, c, v); cell.font = BLUE; cell.fill = YEL; cell.number_format = fmt
    return cell


# ------------------------------------------------------------------ Leyenda
L = wb.active; L.title = 'Leyenda'
lines = [
    ('Economía unitaria · VINCIRENA (marca provisional) · Mercado EE. UU. · USD · V2.1 (13/10/2026)', H1),
    ('Ninguna celda contiene costes, precios ni umbrales reales: se rellenan con cotizaciones, facturas y decisiones del titular. Mientras falte un dato obligatorio, la hoja muestra «DATOS INCOMPLETOS».', BOLD),
    ('', None),
    ('Cómo usarlo', BOLD),
    ('1. Celdas AMARILLAS con texto AZUL = datos editables. NEGRO = fórmulas. VERDE = enlaces entre hojas.', BLACK),
    ('2. Rellena «Costes variables» (columna B) con datos reales por unidad/pedido en USD. Una celda VACÍA = «no lo sé» y bloquea el cálculo; un 0 escrito es un dato válido.', BLACK),
    ('3. «Test de precio»: los precios son PUNTOS DE PRUEBA editables (no precios decididos). Cada fila descuenta TODAS las partidas variables y la comisión real si existe.', BLACK),
    ('4. Impuestos: en EE. UU. el precio se muestra sin sales tax; el impuesto se calcula en el checkout y se ingresa al estado. No se resta del precio (a diferencia del IVA español de la V2).', BLACK),
    ('5. No se modela LTV ni suscripción: el producto es reutilizable. La decisión se basa en el margen del primer pedido.', BLACK),
    ('', None),
    ('Supuestos que hay que verificar', BOLD),
    ('Comisión de pago: 2,9 % + 0,30 $ es un supuesto de partida (tarifa online publicada para planes básicos de Shopify Payments en EE. UU.); confirmar con el plan contratado.', BLACK),
    ('Aranceles: el tratamiento de los envíos de bajo valor importados en EE. UU. (de minimis) ha cambiado recientemente; confirmar con el transitario o agente de aduanas antes de rellenar la partida.', BLACK),
    ('Capital: el titular declaró 1–50 € para España; introducir el importe disponible en USD.', BLACK),
    ('Versión anterior (España, EUR, con IVA): docs/archive/05_ECONOMIA_UNITARIA_ES_V2.xlsx.', BLACK),
]
for i, (t, f) in enumerate(lines, 1):
    c = L.cell(i, 1, t)
    if f: c.font = f
L.column_dimensions['A'].width = 150

# ------------------------------------------------------------------ Supuestos
S = wb.create_sheet('Supuestos')
S['A1'] = 'Supuestos globales (USD)'; S['A1'].font = H1
header(S, 3, ['Supuesto', 'Valor', 'Fuente / nota'])
sup = [
    ('Comisión de pago variable (supuesto)', 0.029, PCT, 'Verificar con el plan de Shopify Payments contratado.'),       # B4
    ('Comisión de pago fija por pedido (supuesto)', 0.30, USD, 'Verificar con el plan contratado.'),                        # B5
    ('Umbral mínimo de contribución por pedido', None, USD, 'Decisión del titular. Vacío = sin veredicto.'),               # B6
    ('Capital disponible para pedidos y reembolsos (USD)', None, USD, 'Dato del titular.'),                                 # B7
    ('CAC de referencia por cliente (USD)', None, USD, 'Dato o hipótesis del titular. Vacío = no se calcula.'),            # B8
    ('Días naturales hasta cobrar la liquidación', None, '0', 'Verificar con Shopify Payments (calendario de pagos).'),   # B9
]
for i, (l, v, fmt, n) in enumerate(sup, 4):
    S.cell(i, 1, l).font = BLACK; inp(S, i, 2, v, fmt); S.cell(i, 3, n).font = BLACK
S.column_dimensions['A'].width = 54; S.column_dimensions['B'].width = 14; S.column_dimensions['C'].width = 70

# ------------------------------------------------------------------ Costes variables (REAL)
C = wb.create_sheet('Costes variables')
C['A1'] = 'Costes variables REALES por pedido de 1 unidad (USD)'; C['A1'].font = H1
C['A2'] = 'Solo datos confirmados (cotizaciones, facturas, tarifas). Vacío = bloquea el cálculo.'; C['A2'].font = BOLD
header(C, 3, ['Partida', 'Valor', 'Obligatoria', 'Fuente / nota'])
rows = [
    ('Producto: coste unitario del proveedor', USD, 'Sí', 'Cotización firmada del modelo exacto.'),                         # 4
    ('Flete internacional / inbound por unidad', USD, 'Sí', 'Prorrateado por unidad.'),                                    # 5
    ('Aranceles, tasas y agente de aduanas por unidad', USD, 'Sí', 'Confirmar régimen vigente con el agente de aduanas.'), # 6
    ('Envío al cliente (última milla)', USD, 'Sí', 'Tarifa real del transportista.'),                                       # 7
    ('Embalaje y preparación (fulfillment)', USD, 'Sí', ''),                                                                 # 8
    ('Reserva por incidencias / contracargos por pedido', USD, 'Sí', 'Pérdidas, daños, fraude.'),                           # 9
    ('Atención al cliente por pedido', USD, 'Sí', 'Tiempo o herramientas imputables.'),                                     # 10
    ('Contenido / colaboradores / afiliados por venta', USD, 'Sí', 'Coste de producción o comisiones por venta. 0 si no hay.'),  # 11
    ('Tasa de devolución esperada', PCT, 'Sí', 'Dato real o prudente; 0 % solo si se documenta.'),                          # 12
    ('Coste por devolución (envío de vuelta + producto no recuperable)', USD, 'Sí', 'Por cada devolución.'),               # 13
    ('Ingreso por envío cobrado al cliente', USD, 'Sí', '0 si el envío es gratuito para el cliente.'),                     # 14
    ('Descuento medio por pedido', USD, 'Sí', '0 si no hay descuentos.'),                                                   # 15
    ('Comisión de pago variable REAL (opcional)', PCT, 'No', 'Vacío = usar Supuestos!B4.'),                                 # 16
    ('Comisión de pago fija REAL (opcional)', USD, 'No', 'Vacío = usar Supuestos!B5.'),                                     # 17
]
for i, (l, fmt, req, n) in enumerate(rows, 4):
    C.cell(i, 1, l).font = BLACK; inp(C, i, 2, None, fmt); C.cell(i, 3, req).font = BLACK; C.cell(i, 4, n).font = BLACK
C['A19'] = 'Partidas obligatorias rellenadas (de 12)'; C['B19'] = '=COUNT(B4:B15)'
C['A20'] = 'Estado'; C['B20'] = f'=IF(B19=12,"COMPLETO","{INC}")'; C['A20'].font = BOLD; C['B20'].font = BOLD
C['A21'] = 'Coste de producto puesto en cliente (filas 4–8)'; C['B21'] = f'=IF($B$20="COMPLETO",SUM(B4:B8),"{INC}")'
C['A22'] = 'Coste esperado de devoluciones por pedido (fila 12 × fila 13)'; C['B22'] = f'=IF($B$20="COMPLETO",B12*B13,"{INC}")'
C['A23'] = 'Otros costes variables por pedido (filas 9–11)'; C['B23'] = f'=IF($B$20="COMPLETO",SUM(B9:B11),"{INC}")'
C['A24'] = 'Coste variable total por pedido (antes de comisión)'; C['B24'] = f'=IF($B$20="COMPLETO",B21+B22+B23,"{INC}")'
C['A25'] = 'Comisión variable usada'; C['B25'] = '=IF(B16="",Supuestos!B4,B16)'
C['A26'] = 'Comisión fija usada'; C['B26'] = '=IF(B17="",Supuestos!B5,B17)'
C['A27'] = 'Desembolso antes de cobrar (filas 4–8)'; C['B27'] = f'=IF($B$20="COMPLETO",SUM(B4:B8),"{INC}")'
for r in (21, 22, 23, 24, 26, 27): C.cell(r, 2).number_format = USD
C['B25'].number_format = PCT
for r in (24,): C.cell(r, 1).font = BOLD; C.cell(r, 2).font = BOLD
C.conditional_formatting.add('B20:B27', FormulaRule(formula=[f'B20="{INC}"'], fill=REDF))
C.column_dimensions['A'].width = 62; C.column_dimensions['B'].width = 16; C.column_dimensions['C'].width = 12; C.column_dimensions['D'].width = 54

# ------------------------------------------------------------------ Test de precio
P = wb.create_sheet('Test de precio')
P['A1'] = 'Test de precio · puntos de prueba en USD (no son precios decididos)'; P['A1'].font = H1
P['A2'] = 'Cada fila descuenta TODAS las partidas de «Costes variables» y la comisión real si existe.'; P['A2'].font = BOLD
cols = ['Precio de prueba (sin sales tax)', 'Ingreso del pedido (precio − descuento + envío cobrado)', 'Comisión de pago', 'Coste producto puesto en cliente',
        'Devoluciones esperadas', 'Incidencias + atención + contenido', 'Contribución por pedido', 'Veredicto frente al umbral', 'Contribución tras CAC']
header(P, 4, cols)
for i, price in enumerate([24.99, 29.99, 34.99], 5):
    inp(P, i, 1, price)
    ok = "'Costes variables'!$B$20=\"COMPLETO\""
    P.cell(i, 2, f'=IF(A{i}="","—",A{i}-\'Costes variables\'!$B$15+\'Costes variables\'!$B$14)').number_format = USD
    P.cell(i, 3, f'=IF(A{i}="","—",B{i}*\'Costes variables\'!$B$25+\'Costes variables\'!$B$26)').number_format = USD
    P.cell(i, 4, "='Costes variables'!$B$21").number_format = USD
    P.cell(i, 5, "='Costes variables'!$B$22").number_format = USD
    P.cell(i, 6, "='Costes variables'!$B$23").number_format = USD
    c = P.cell(i, 7, f'=IF(OR(A{i}="",NOT({ok})),"{INC}",B{i}-C{i}-D{i}-E{i}-F{i})'); c.number_format = USD; c.font = BOLD
    P.cell(i, 8, f'=IF(G{i}="{INC}","{INC}",IF(Supuestos!$B$6="","Umbral sin definir",IF(G{i}>=Supuestos!$B$6,"Supera umbral","No supera")))').font = BOLD
    P.cell(i, 9, f'=IF(G{i}="{INC}","{INC}",IF(Supuestos!$B$8="","CAC sin definir",G{i}-Supuestos!$B$8))').number_format = USD
    for j in (4, 5, 6): P.cell(i, j).font = GREEN
P.conditional_formatting.add('G5:I7', FormulaRule(formula=[f'G5="{INC}"'], fill=REDF))
P['A9'] = 'Comprobación: contribución = ingreso − comisión − coste producto − devoluciones − (incidencias + atención + contenido). Ninguna partida se omite.'
for j, w in enumerate([18, 24, 14, 18, 16, 20, 18, 22, 18], 1): P.column_dimensions[P.cell(1, j).column_letter].width = w

# ------------------------------------------------------------------ Capital circulante
K = wb.create_sheet('Capital circulante')
K['A1'] = 'Capital necesario antes de cobrar las liquidaciones (USD)'; K['A1'].font = H1
header(K, 3, ['Concepto', 'Valor', 'Nota'])
K['A4'] = 'Pedidos por día a cubrir'; inp(K, 4, 2, None, '0.0'); K['C4'] = 'Escenario de ventas del titular'
K['A5'] = 'Días hasta cobrar'; K['B5'] = '=Supuestos!B9'; K['B5'].font = GREEN
K['A6'] = 'Desembolso por pedido antes de cobrar'; K['B6'] = "='Costes variables'!B27"; K['B6'].font = GREEN; K['B6'].number_format = USD
K['A7'] = 'Colchón para reembolsos (pedidos equivalentes)'; inp(K, 7, 2, None, '0'); K['C7'] = 'Decisión del titular'
K['A8'] = 'Capital necesario'; K['B8'] = f'=IF(OR(B4="",B5="",B7="",B6="{INC}"),"{INC}",B4*B5*B6+B7*B6)'; K['B8'].number_format = USD; K['A8'].font = BOLD; K['B8'].font = BOLD
K['A9'] = 'Capital disponible'; K['B9'] = '=IF(Supuestos!B7="","—",Supuestos!B7)'; K['B9'].font = GREEN; K['B9'].number_format = USD
K['A10'] = '¿Suficiente?'; K['B10'] = f'=IF(OR(B8="{INC}",B9="—"),"{INC}",IF(B9>=B8,"Sí","INSUFICIENTE"))'; K['B10'].font = BOLD
for c, w in zip('ABC', (48, 16, 40)): K.column_dimensions[c].width = w

# ------------------------------------------------------------------ Panel semanal
W = wb.create_sheet('Panel semanal')
W['A1'] = 'Panel semanal (datos de Shopify Analytics, en USD)'; W['A1'].font = H1
W['A2'] = 'Precio de venta actual (USD, sin sales tax):'; inp(W, 2, 4, None)
cols = ['Semana', 'Sesiones', 'Sesiones con vista de producto', 'Sesiones con ATC', 'Sesiones con checkout', 'Pedidos', 'Ventas brutas (USD)',
        'Gasto de captación (USD)', 'Coste de contenido (USD)', 'Devoluciones (nº)',
        'Conversión tienda', 'ATC / vistas producto', 'Checkout / ATC', 'AOV', 'CAC', 'Contribución estimada', 'Tasa devolución']
header(W, 3, cols)
contrib_unit = (f"IF(OR($D$2=\"\",'Costes variables'!$B$20<>\"COMPLETO\"),\"{INC}\","
                f"($D$2-'Costes variables'!$B$15+'Costes variables'!$B$14)*(1-'Costes variables'!$B$25)-'Costes variables'!$B$26-'Costes variables'!$B$24)")
for i in range(4, 16):
    for j in range(1, 11):
        inp(W, i, j, None, '#,##0' if j not in (7, 8, 9) else USD)
    W.cell(i, 1).number_format = '@'
    W.cell(i, 11, f'=IF(OR(B{i}="",B{i}=0,F{i}=""),"",F{i}/B{i})').number_format = PCT
    W.cell(i, 12, f'=IF(OR(C{i}="",C{i}=0,D{i}=""),"",D{i}/C{i})').number_format = PCT
    W.cell(i, 13, f'=IF(OR(D{i}="",D{i}=0,E{i}=""),"",E{i}/D{i})').number_format = PCT
    W.cell(i, 14, f'=IF(OR(F{i}="",F{i}=0,G{i}=""),"",G{i}/F{i})').number_format = USD
    W.cell(i, 15, f'=IF(OR(F{i}="",F{i}=0,H{i}=""),"",(H{i}+IF(I{i}="",0,I{i}))/F{i})').number_format = USD
    W.cell(i, 16, f'=IF(F{i}="","",IF(ISNUMBER({contrib_unit}),F{i}*{contrib_unit},"{INC}"))').number_format = USD
    W.cell(i, 17, f'=IF(OR(F{i}="",F{i}=0,J{i}=""),"",J{i}/F{i})').number_format = PCT
W['A17'] = 'Definiciones: conversión = pedidos/sesiones · ATC = sesiones con añadir al carrito / sesiones con vista de producto · checkout = sesiones con checkout / sesiones con ATC · AOV = ventas brutas / pedidos · CAC = (captación + contenido) / pedidos. Las visualizaciones en redes no son sesiones.'
for j in range(1, 18): W.column_dimensions[W.cell(1, j).column_letter].width = 14

# ------------------------------------------------------------------ Sensibilidad
T = wb.create_sheet('Sensibilidad')
T['A1'] = 'Sensibilidad de adquisición (planificación, no previsión)'; T['A1'].font = H1
T['A2'] = 'Contribución usada (Test de precio, fila elegida):'; inp(T, 2, 5, 2, '0'); T['F2'] = '← 1, 2 o 3 = fila 5, 6 o 7 de «Test de precio»'
T['C3'] = "=INDEX('Test de precio'!G5:G7,E2)"; T['A3'] = 'Contribución por pedido:'; T['C3'].font = GREEN; T['C3'].number_format = USD
header(T, 5, ['Sesiones cualificadas/mes', 'Conversión hipotética', 'Pedidos teóricos', 'Contribución total', 'Capital a adelantar'])
for i in range(6, 10):
    inp(T, i, 1, None, '#,##0'); inp(T, i, 2, None, PCT)
    T.cell(i, 3, f'=IF(OR(A{i}="",B{i}=""),"",A{i}*B{i})').number_format = '0.0'
    T.cell(i, 4, f'=IF(C{i}="","",IF(ISNUMBER($C$3),C{i}*$C$3,"{INC}"))').number_format = USD
    T.cell(i, 5, f"=IF(C{i}=\"\",\"\",IF(ISNUMBER('Costes variables'!$B$27),C{i}*'Costes variables'!$B$27,\"{INC}\"))").number_format = USD
for c, w in zip('ABCDEF', (26, 20, 18, 20, 22, 40)): T.column_dimensions[c].width = w

for ws in wb.worksheets:
    for row in ws.iter_rows():
        for c in row:
            f = c.font; c.font = Font(name=F, bold=f.bold, size=f.size, color=f.color)
wb.save(OUT)
print('ok', OUT)

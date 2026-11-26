"""Boleto navideño A4 para Auditorio Plata.

Mantiene exactamente la función utilizada por servidor/main.py:
    crear_pdf_boleto(folio: int, evento: str, fecha_emision: datetime, tipo_boleto: str = "GENERAL") -> bytes

El artista es ficticio y se usa solamente como demostración.
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from math import cos, sin, pi

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ARTISTA = "La Garantía Norteña"

VERDE = colors.HexColor("#195747")
VERDE_OSCURO = colors.HexColor("#124236")
ROJO = colors.HexColor("#D74D3E")
DORADO = colors.HexColor("#CFA35D")
CREMA = colors.HexColor("#FAF7EF")
BLANCO = colors.HexColor("#FFFFFF")
TEXTO = colors.HexColor("#23483D")
GRIS = colors.HexColor("#66796D")


def _fuente(nombre, rutas, alternativa):
    if nombre in pdfmetrics.getRegisteredFontNames():
        return nombre
    for ruta in rutas:
        if Path(ruta).is_file():
            try:
                pdfmetrics.registerFont(TTFont(nombre, ruta))
                return nombre
            except Exception:
                pass
    return alternativa


def _tipos():
    regular = _fuente("APRegular", [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ], "Helvetica")
    negrita = _fuente("APBold", [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ], "Helvetica-Bold")
    titulo = _fuente("APSerif", [
        r"C:\Windows\Fonts\georgiab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ], "Times-Bold")
    return regular, negrita, titulo


def _centrar(pdf, texto, x, y, fuente, tam, max_ancho):
    # Reducir el tamaño si el texto es más largo que el espacio disponible.
    while tam > 9 and pdfmetrics.stringWidth(texto, fuente, tam) > max_ancho:
        tam -= 0.5
    pdf.setFont(fuente, tam)
    pdf.drawCentredString(x, y, texto)


def _estrella(pdf, x, y, radio=15):
    p = pdf.beginPath()
    for i in range(10):
        ang = pi / 2 + i * pi / 5
        r = radio if i % 2 == 0 else radio * 0.43
        px, py = x + r * cos(ang), y + r * sin(ang)
        if i == 0:
            p.moveTo(px, py)
        else:
            p.lineTo(px, py)
    p.close()
    pdf.setFillColor(DORADO)
    pdf.drawPath(p, stroke=0, fill=1)


def _arbol(pdf, x, y, escala=1):
    """Árbol vectorial que cabe en un área de 175 x 220 puntos."""
    pdf.saveState()
    pdf.translate(x, y)
    pdf.scale(escala, escala)
    pdf.setFillColor(colors.HexColor("#83563D"))
    pdf.roundRect(-11, 0, 22, 44, 3, fill=1, stroke=0)
    for ancho, base, punta, color in [
        (138, 40, 148, "#1B604E"),
        (111, 91, 185, "#23765D"),
        (79, 135, 217, "#2E896A"),
    ]:
        p = pdf.beginPath()
        p.moveTo(0, punta)
        p.lineTo(ancho / 2, base)
        p.lineTo(-ancho / 2, base)
        p.close()
        pdf.setFillColor(colors.HexColor(color))
        pdf.drawPath(p, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#F5D887"))
    pdf.setLineWidth(3)
    for y0, medio in [(116, 89), (74, 49)]:
        p = pdf.beginPath()
        p.moveTo(-medio * 0.85, y0 + 17)
        p.curveTo(-medio * .55, y0 - 5, medio * .55, y0 - 5, medio * .85, y0 + 17)
        pdf.drawPath(p, stroke=1, fill=0)
    for px, py, col in [
        (-22, 164, ROJO), (15, 144, DORADO), (-35, 107, DORADO),
        (30, 91, ROJO), (0, 72, colors.HexColor("#E8A87C")),
        (-15, 123, colors.HexColor("#FFCF6F")),
    ]:
        pdf.setFillColor(col)
        pdf.circle(px, py, 5, fill=1, stroke=0)
    _estrella(pdf, 0, 226, 17)
    pdf.restoreState()


def _regalo(pdf, x, y, ancho, alto, color):
    pdf.setFillColor(color)
    pdf.roundRect(x, y, ancho, alto, 3, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#FFF6DB"))
    pdf.rect(x + ancho / 2 - 3, y, 6, alto, fill=1, stroke=0)
    pdf.rect(x, y + alto * .61, ancho, 5, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#FFF6DB"))
    pdf.setLineWidth(2.5)
    pdf.circle(x + ancho / 2 - 6, y + alto + 2, 6, fill=0, stroke=1)
    pdf.circle(x + ancho / 2 + 6, y + alto + 2, 6, fill=0, stroke=1)


def _rama(pdf, x, y, espejo=1):
    pdf.saveState()
    pdf.translate(x, y)
    pdf.scale(espejo, 1)
    pdf.setStrokeColor(VERDE)
    pdf.setLineWidth(2)
    pdf.line(0, 0, 66, -31)
    for dx in range(11, 64, 11):
        yy = -dx * 0.47
        pdf.line(dx, yy, dx - 9, yy + 18)
        pdf.line(dx, yy, dx + 8, yy - 14)
    pdf.setFillColor(ROJO)
    for px, py in [(16, -4), (25, -10), (21, -17)]:
        pdf.circle(px, py, 4.5, stroke=0, fill=1)
    pdf.restoreState()


TEMAS = {
    "GENERAL": {
        "fondo": "#A8D4C3", "marco": "#FAF7EF", "tarjeta": "#FFFFFF",
        "cabecera": "#124236", "acento": "#CFA35D", "titulo": "#195747",
        "texto": "#23483D", "suave": "#66796D", "folio": "#D74D3E",
        "caja": "#F4F8F1", "linea": "#D9E5D9", "subtitulo": "#EAD69D",
    },
    "PREFERENTE": {
        "fondo": "#7A263B", "marco": "#D5D7DD", "tarjeta": "#FFF9FA",
        "cabecera": "#631E31", "acento": "#C7C9CF", "titulo": "#7A263B",
        "texto": "#382A32", "suave": "#6D5360", "folio": "#7A263B",
        "caja": "#F0E9EE", "linea": "#D7C7CF", "subtitulo": "#E7E7EB",
    },
    "VIP": {
        "fondo": "#141414", "marco": "#34302A", "tarjeta": "#222222",
        "cabecera": "#111111", "acento": "#D4AF37", "titulo": "#F4DA86",
        "texto": "#F8F2DD", "suave": "#D9CDA9", "folio": "#EAC95C",
        "caja": "#34302A", "linea": "#62543A", "subtitulo": "#F4DA86",
    },
}


def crear_pdf_boleto(folio: int, evento: str, fecha_emision: datetime, tipo_boleto: str = "GENERAL") -> bytes:
    tipo_boleto = (tipo_boleto or "GENERAL").strip().upper()
    if tipo_boleto not in TEMAS:
        raise ValueError("Tipo de boleto no válido")
    tema = TEMAS[tipo_boleto]

    def color(nombre):
        return colors.HexColor(tema[nombre])

    regular, bold, serif = _tipos()
    codigo = f"AP-{folio:06d}"
    fecha = fecha_emision.strftime("%d/%m/%Y")
    hora = fecha_emision.strftime("%H:%M:%S %z").strip()

    # UTF-8 con marca BOM para mejorar su interpretación en lectores móviles.
    # Algunos lectores antiguos pueden seguir tratando el texto como otro juego de caracteres.
    qr_texto = (
        "AUDITORIO PLATA\n"
        f"Evento: {evento}\n"
        f"Artista: {ARTISTA}\n"
        f"Tipo: {tipo_boleto}\n"
        f"Folio: {codigo}\n"
        f"Fecha: {fecha}\n"
        f"Hora: {hora}\n"
        f"FechaHoraISO: {fecha_emision.isoformat()}"
    )
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_texto.encode("utf-8-sig"), optimize=0)
    qr.make(fit=True)
    imagen_qr = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    salida = BytesIO()
    pdf = canvas.Canvas(salida, pagesize=A4)
    w, h = A4
    centro = w / 2
    pdf.setTitle(f"Boleto {tipo_boleto} {codigo} - Auditorio Plata")
    pdf.setAuthor("Auditorio Plata")

    # Fondo crema y tarjeta principal; nada queda fuera de la hoja A4.
    pdf.setFillColor(color("fondo"))
    pdf.rect(0, 0, w, h, stroke=0, fill=1)
    pdf.setFillColor(color("marco"))
    pdf.roundRect(26, 30, w - 52, h - 60, 20, stroke=0, fill=1)
    pdf.setFillColor(color("tarjeta"))
    pdf.roundRect(37, 41, w - 74, h - 82, 15, stroke=0, fill=1)
    pdf.setStrokeColor(color("acento"))
    pdf.setLineWidth(1.8)
    pdf.roundRect(37, 41, w - 74, h - 82, 15, stroke=1, fill=0)

    # Cabecera completamente dentro de la tarjeta.
    pdf.setFillColor(color("cabecera"))
    pdf.roundRect(49, 679, w - 98, 102, 12, fill=1, stroke=0)
    pdf.setFillColor(color("acento"))
    pdf.rect(49, 679, w - 98, 3, fill=1, stroke=0)
    pdf.setFillColor(BLANCO)
    _centrar(pdf, "AUDITORIO PLATA", centro, 737, serif, 25, 405)
    pdf.setFillColor(color("subtitulo"))
    _centrar(pdf, f"BOLETO {tipo_boleto} · ENTRADA GRATUITA", centro, 713, bold, 10, 430)
    _rama(pdf, 65, 771, 1)
    _rama(pdf, w - 65, 771, -1)

    pdf.setFillColor(color("folio"))
    pdf.setFont(bold, 9)
    pdf.drawCentredString(centro, 650, "EDICIÓN ESPECIAL DE NAVIDAD")
    pdf.setFillColor(color("titulo"))
    _centrar(pdf, evento, centro, 619, serif, 24, 465)

    pdf.setFillColor(color("texto"))
    _centrar(pdf, f"Artista: {ARTISTA}", centro, 591, bold, 13, 465)
    pdf.setStrokeColor(color("linea"))
    pdf.line(85, 563, w - 85, 563)

    pdf.setFillColor(color("suave"))
    pdf.setFont(bold, 9)
    pdf.drawCentredString(centro, 544, "FOLIO DE ENTRADA")
    pdf.setFillColor(color("folio"))
    pdf.setFont(bold, 19)
    pdf.drawCentredString(centro, 521, codigo)

    # Fecha y hora en cajas distintas, con márgenes seguros.
    for x in (78, 308):
        pdf.setFillColor(color("caja"))
        pdf.roundRect(x, 447, 207, 55, 9, fill=1, stroke=0)
    pdf.setFillColor(color("suave"))
    pdf.setFont(bold, 8.5)
    pdf.drawCentredString(181.5, 481, "FECHA DE EMISIÓN")
    pdf.drawCentredString(411.5, 481, "HORA DE EMISIÓN")
    pdf.setFillColor(color("texto"))
    _centrar(pdf, fecha, 181.5, 461, bold, 12, 187)
    _centrar(pdf, hora, 411.5, 461, bold, 11, 187)

    # Zona inferior: árbol a la izquierda, QR a la derecha, sin superposición.
    _arbol(pdf, 164, 199, 0.82)
    _regalo(pdf, 99, 187, 39, 37, ROJO)
    _regalo(pdf, 140, 182, 48, 43, DORADO)
    _regalo(pdf, 192, 188, 37, 32, colors.HexColor("#6DACA0"))

    qr_x, qr_y, qr_lado = 307, 203, 194
    pdf.setFillColor(BLANCO)
    pdf.roundRect(qr_x - 8, qr_y - 8, qr_lado + 16, qr_lado + 16, 10, stroke=0, fill=1)
    pdf.drawImage(ImageReader(imagen_qr), qr_x, qr_y,
                  width=qr_lado, height=qr_lado, mask='auto')
    pdf.setFillColor(color("suave"))
    _centrar(pdf, "ESCANEA TU CÓDIGO QR", qr_x + qr_lado/2, 184, bold, 9.2, 210)

    pdf.setStrokeColor(color("linea"))
    pdf.setDash(4, 4)
    pdf.line(85, 153, w - 85, 153)
    pdf.setDash()
    pdf.setFillColor(color("titulo"))
    pdf.setFont(bold, 10.5)
    pdf.drawCentredString(centro, 131, "ENTRADA GRATUITA")
    pdf.setFillColor(color("suave"))
    _centrar(pdf, "Conserva tu boleto y presenta el QR al ingresar", centro, 113, regular, 9, 440)
    pdf.setFillColor(color("titulo"))
    _centrar(pdf, "AUDITORIO PLATA · UNA NAVIDAD PARA RECORDAR", centro, 68, bold, 8.5, 445)

    pdf.save()
    datos = salida.getvalue()
    salida.close()
    return datos

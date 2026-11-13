
from io import BytesIO
from datetime import datetime

import qrcode

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors


def crear_pdf_boleto(
    folio: int,
    evento: str,
    fecha_emision: datetime
) -> bytes:

    codigo = f"AP-{folio:06d}"

    fecha = fecha_emision.strftime("%d/%m/%Y")
    hora = fecha_emision.strftime("%H:%M:%S %z").strip()

    # =====================================
    # GENERAR CODIGO QR
    # =====================================

    datos_qr = (
        "AUDITORIO PLATA\n"
        f"Evento: {evento}\n"
        f"Folio: {codigo}\n"
        f"Fecha: {fecha}\n"
        f"Hora: {hora}\n"
        f"FechaHoraISO: {fecha_emision.isoformat()}"
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(datos_qr)
    qr.make(fit=True)

    imagen_qr = qr.make_image(
        fill_color="black",
        back_color="white"
    ).convert("RGB")

    # =====================================
    # GENERAR PDF EN MEMORIA
    # =====================================

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4
    )

    ancho, alto = A4

    pdf.setTitle(f"Boleto {codigo} - Auditorio Plata")

    # Fondo
    pdf.setFillColor(colors.HexColor("#F5F6FA"))
    pdf.rect(0, 0, ancho, alto, fill=1, stroke=0)

    # Tarjeta del boleto
    pdf.setFillColor(colors.white)
    pdf.roundRect(
        45, 170,
        ancho - 90, 560,
        18,
        fill=1,
        stroke=0
    )

    # Encabezado
    pdf.setFillColor(colors.HexColor("#253858"))
    pdf.setFont("Helvetica-Bold", 26)

    pdf.drawCentredString(
        ancho / 2, 675,
        "AUDITORIO PLATA"
    )

    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(
        ancho / 2, 646,
        "BOLETO DE ENTRADA GRATUITA"
    )

    # Evento
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 19)

    pdf.drawCentredString(
        ancho / 2, 602,
        evento
    )

    # Folio
    pdf.setFont("Helvetica-Bold", 15)

    pdf.drawCentredString(
        ancho / 2, 558,
        f"Folio: {codigo}"
    )

    # Fecha y hora
    pdf.setFont("Helvetica", 12)

    pdf.drawCentredString(
        ancho / 2, 527,
        f"Fecha de emision: {fecha}"
    )

    pdf.drawCentredString(
        ancho / 2, 506,
        f"Hora de emision: {hora}"
    )

    # Código QR
    imagen = ImageReader(imagen_qr)

    qr_tamano = 210

    pdf.drawImage(
        imagen,
        (ancho - qr_tamano) / 2,
        275,
        width=qr_tamano,
        height=qr_tamano
    )

    # Texto inferior
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#555555"))

    pdf.drawCentredString(
        ancho / 2, 240,
        "Escanea el QR para consultar los datos del boleto"
    )

    pdf.drawCentredString(
        ancho / 2, 215,
        "Conserva este boleto para tu ingreso"
    )

    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(
        ancho / 2, 105,
        "Sistema Auditorio Plata - Entrada gratuita"
    )

    # Finalizar documento
    pdf.save()

    contenido = buffer.getvalue()
    buffer.close()

    return contenido

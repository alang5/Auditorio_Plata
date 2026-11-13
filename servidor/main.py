
import threading
from datetime import datetime, timezone
from uuid import UUID, uuid4

import oracledb
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from servidor.boletos_pdf import crear_pdf_boleto
from pydantic import BaseModel, Field

from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from servidor.database import conectar
from servidor.readers_writers import ReadersWriters


# ========================================
# CONFIGURACIÓN DEL SERVIDOR
# ========================================

app = FastAPI(
    title="Auditorio Plata",
    description="Sistema de emisión de boletos gratuitos",
    version="1.0.0"
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)

rw = ReadersWriters()

EVENTO_ID = 1


class SolicitudBoleto(BaseModel):
    solicitud_id: UUID = Field(default_factory=uuid4)
    hilo_id: str = Field(default="manual", max_length=100)


# ========================================
# FUNCIONES AUXILIARES
# ========================================

def registrar_bitacora(
    cursor, solicitud_id, hilo_id,
    hora_inicio, folio, estado, detalle
):
    cursor.execute("""
        INSERT INTO bitacora (
            solicitud_id,
            hilo_id,
            hora_envio,
            hora_respuesta,
            folio,
            estado,
            detalle
        )
        VALUES (
            :solicitud_id,
            :hilo_id,
            :hora_inicio,
            SYSTIMESTAMP,
            :folio,
            :estado,
            :detalle
        )
    """, {
        "solicitud_id": solicitud_id,
        "hilo_id": hilo_id,
        "hora_inicio": hora_inicio,
        "folio": folio,
        "estado": estado,
        "detalle": detalle
    })


def formato_folio(numero):
    return f"AP-{numero:06d}"


# ========================================
# ENDPOINT 1: INICIO
# ========================================


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(STATIC_DIR / "index.html")


# ========================================
# ENDPOINT 2: CONSULTAR AFORO
# READERS
# ========================================

@app.get("/aforo")
def consultar_aforo():

    with rw.lector():

        try:
            with conectar() as conexion:
                with conexion.cursor() as cursor:

                    cursor.execute("""
                        SELECT nombre, aforo, emitidos
                        FROM eventos
                        WHERE id = :id
                    """, {"id": EVENTO_ID})

                    evento = cursor.fetchone()

                    if evento is None:
                        raise HTTPException(
                            status_code=404,
                            detail="Evento no encontrado"
                        )

                    nombre, aforo, emitidos = evento

                    return {
                        "evento": nombre,
                        "aforo": aforo,
                        "emitidos": emitidos,
                        "disponibles": aforo - emitidos
                    }

        except HTTPException:
            raise

        except oracledb.Error:
            raise HTTPException(
                status_code=503,
                detail="Error de conexión con Oracle"
            )


# ========================================
# ENDPOINT 3: SOLICITAR BOLETO
# WRITERS
# ========================================

@app.post("/boletos")
def solicitar_boleto(datos: SolicitudBoleto):

    solicitud_id = str(datos.solicitud_id)
    hilo_id = datos.hilo_id
    hora_inicio = datetime.now(timezone.utc)

    # SECCIÓN CRÍTICA: WRITER
    with rw.escritor():

        try:
            with conectar() as conexion:

                try:
                    with conexion.cursor() as cursor:

                        # Bloquear la fila del concierto
                        cursor.execute("""
                            SELECT aforo, emitidos
                            FROM eventos
                            WHERE id = :id
                            FOR UPDATE
                        """, {"id": EVENTO_ID})

                        evento = cursor.fetchone()

                        if evento is None:
                            raise HTTPException(
                                status_code=404,
                                detail="Evento no encontrado"
                            )

                        aforo, emitidos = evento

                        # Comprobar si esta solicitud
                        # ya había generado un boleto
                        cursor.execute("""
                            SELECT folio, fecha_emision
                            FROM boletos
                            WHERE solicitud_id = :sid
                        """, {"sid": solicitud_id})

                        existente = cursor.fetchone()

                        if existente is not None:

                            folio, fecha = existente

                            registrar_bitacora(
                                cursor, solicitud_id,
                                hilo_id, hora_inicio,
                                folio, "EXITO",
                                "Reintento: boleto existente"
                            )

                            conexion.commit()

                            return JSONResponse(
                                status_code=200,
                                content={
                                    "estado": "EXITO",
                                    "mensaje": "Boleto existente",
                                    "folio": formato_folio(folio),
                                    "solicitud_id": solicitud_id,
                                    "fecha_emision": fecha.isoformat()
                                }
                            )

                        # Verificar capacidad
                        if emitidos >= aforo:

                            registrar_bitacora(
                                cursor, solicitud_id,
                                hilo_id, hora_inicio,
                                None, "RECHAZO",
                                "Aforo agotado"
                            )

                            conexion.commit()

                            raise HTTPException(
                                status_code=409,
                                detail="Aforo agotado"
                            )

                        # Generar folio desde Oracle
                        cursor.execute(
                            "SELECT seq_folio.NEXTVAL FROM dual"
                        )

                        folio = cursor.fetchone()[0]

                        # Guardar boleto
                        cursor.execute("""
                            INSERT INTO boletos (
                                folio,
                                evento_id,
                                solicitud_id
                            )
                            VALUES (
                                :folio,
                                :evento_id,
                                :solicitud_id
                            )
                        """, {
                            "folio": folio,
                            "evento_id": EVENTO_ID,
                            "solicitud_id": solicitud_id
                        })

                        # Actualizar aforo
                        cursor.execute("""
                            UPDATE eventos
                            SET emitidos = emitidos + 1
                            WHERE id = :id
                        """, {"id": EVENTO_ID})

                        # Consultar fecha oficial
                        cursor.execute("""
                            SELECT fecha_emision
                            FROM boletos
                            WHERE folio = :folio
                        """, {"folio": folio})

                        fecha = cursor.fetchone()[0]

                        # Registrar solicitud exitosa
                        registrar_bitacora(
                            cursor, solicitud_id,
                            hilo_id, hora_inicio,
                            folio, "EXITO",
                            "Boleto emitido"
                        )

                        # Confirmar toda la transacción
                        conexion.commit()

                        return JSONResponse(
                            status_code=201,
                            content={
                                "estado": "EXITO",
                                "mensaje": "Boleto emitido",
                                "folio": formato_folio(folio),
                                "solicitud_id": solicitud_id,
                                "fecha_emision": fecha.isoformat(),
                                "disponibles": aforo - emitidos - 1
                            }
                        )

                except Exception:
                    conexion.rollback()
                    raise

        except HTTPException:
            raise

        except oracledb.Error:
            raise HTTPException(
                status_code=503,
                detail="No se pudo procesar la solicitud en Oracle"
            )


# ========================================
# ENDPOINT 4: DESCARGAR BOLETO PDF
# READERS
# ========================================

@app.get("/boletos/{folio}/pdf")
def descargar_boleto(folio: int):

    if folio <= 0:
        raise HTTPException(
            status_code=400,
            detail="Folio inválido"
        )

    try:
        # Sección de lectura
        with rw.lector():

            with conectar() as conexion:

                with conexion.cursor() as cursor:

                    cursor.execute("""
                        SELECT
                            b.folio,
                            b.fecha_emision,
                            e.nombre
                        FROM boletos b
                        INNER JOIN eventos e
                            ON b.evento_id = e.id
                        WHERE b.folio = :folio
                    """, {"folio": folio})

                    boleto = cursor.fetchone()

    except oracledb.Error:
        raise HTTPException(
            status_code=503,
            detail="No se pudo consultar Oracle"
        )

    if boleto is None:
        raise HTTPException(
            status_code=404,
            detail="Boleto no encontrado"
        )

    numero, fecha, evento = boleto

    # Generar PDF fuera del bloqueo de lectura
    try:
        archivo_pdf = crear_pdf_boleto(
            folio=numero,
            evento=evento,
            fecha_emision=fecha
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error al generar el PDF"
        )

    nombre_archivo = f"AP-{numero:06d}.pdf"

    return Response(
        content=archivo_pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="{nombre_archivo}"',
            "Cache-Control": "no-store"
        }
    )

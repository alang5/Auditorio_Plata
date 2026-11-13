
import csv
import threading
import time
import uuid

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from servidor.readers_writers import ReadersWriters


app = FastAPI(title="Auditorio Plata - Laboratorio")

URL_LOCAL = "http://127.0.0.1:8001"
TOTAL = 10
AFORO = 3

experimentos = {}
mutex_experimentos = threading.Lock()


class DatosSolicitud(BaseModel):
    hilo_id: str


class Experimento:

    def __init__(self, modo):
        self.modo = modo
        self.aforo = AFORO
        self.emitidos = 0

        self.rw = ReadersWriters()

        # Coordina la llegada de los 10 hilos
        self.barrera = threading.Barrier(TOTAL)

    def solicitar(self):

        if self.modo == "sin":

            # Lectura NO protegida del recurso compartido
            valor_leido = self.emitidos

            # Todos leen antes de que alguien escriba
            self.barrera.wait(timeout=15)

            if valor_leido >= self.aforo:
                return {
                    "estado": "RECHAZO",
                    "folio": None
                }

            # Ampliar intencionalmente la ventana
            # de la condición de carrera
            time.sleep(0.02)

            # Escritura sin exclusión mutua
            self.emitidos = valor_leido + 1

            return {
                "estado": "EXITO",
                "folio": f"AP-{valor_leido + 1:06d}"
            }

        # Todos llegan antes de competir por el lock
        self.barrera.wait(timeout=15)

        # Sección crítica protegida
        with self.rw.escritor():

            if self.emitidos >= self.aforo:
                return {
                    "estado": "RECHAZO",
                    "folio": None
                }

            self.emitidos += 1

            return {
                "estado": "EXITO",
                "folio": f"AP-{self.emitidos:06d}"
            }


@app.get("/")
def pagina():
    archivo = Path(__file__).with_name("demo_web.html")
    return FileResponse(archivo)


# Endpoint que recibe cada solicitud HTTP real
@app.post("/api/emitir/{experimento_id}")
def emitir(experimento_id: str, datos: DatosSolicitud):

    with mutex_experimentos:
        experimento = experimentos.get(experimento_id)

    if experimento is None:
        raise HTTPException(404, "Experimento no encontrado")

    try:
        resultado = experimento.solicitar()

    except threading.BrokenBarrierError:
        raise HTTPException(
            503,
            "No llegaron todos los hilos a la barrera"
        )

    resultado["hilo_id"] = datos.hilo_id

    codigo = (
        201 if resultado["estado"] == "EXITO"
        else 409
    )

    return JSONResponse(
        status_code=codigo,
        content=resultado
    )


# Un hilo solicitante: una petición HTTP
def solicitar_http(experimento_id, numero):

    hilo_id = f"spawner-{numero:03d}"

    registro = {
        "hilo_id": hilo_id,
        "hora_envio": "",
        "hora_respuesta": "",
        "latencia_ms": 0,
        "folio": "",
        "estado": "ERROR",
        "http": 0
    }

    registro["hora_envio"] = (
        datetime.now().astimezone().isoformat(
            timespec="milliseconds"
        )
    )

    inicio = time.perf_counter()

    try:
        respuesta = requests.post(
            f"{URL_LOCAL}/api/emitir/{experimento_id}",
            json={"hilo_id": hilo_id},
            timeout=20
        )

        registro["http"] = respuesta.status_code

        datos = respuesta.json()

        if respuesta.status_code == 201:
            registro["estado"] = "EXITO"
            registro["folio"] = datos["folio"]

        elif respuesta.status_code == 409:
            registro["estado"] = "RECHAZO"

    except (requests.RequestException, ValueError, KeyError):
        registro["estado"] = "ERROR"

    finally:
        registro["hora_respuesta"] = (
            datetime.now().astimezone().isoformat(
                timespec="milliseconds"
            )
        )

        registro["latencia_ms"] = round(
            (time.perf_counter() - inicio) * 1000,
            2
        )

    return registro


# Endpoint utilizado por los botones de la página
@app.post("/api/experimentar/{modo}")
def ejecutar_experimento(modo: str):

    if modo not in ("sin", "con"):
        raise HTTPException(400, "Modo no válido")

    experimento_id = str(uuid.uuid4())
    prueba = Experimento(modo)

    with mutex_experimentos:
        experimentos[experimento_id] = prueba

    inicio = time.perf_counter()

    try:
        # 10 hilos que envían 10 solicitudes HTTP reales
        with ThreadPoolExecutor(max_workers=TOTAL) as pool:

            registros = list(
                pool.map(
                    lambda numero: solicitar_http(
                        experimento_id, numero
                    ),
                    range(1, TOTAL + 1)
                )
            )

    finally:
        with mutex_experimentos:
            experimentos.pop(experimento_id, None)

    duracion = time.perf_counter() - inicio

    exitosos = [
        r for r in registros
        if r["estado"] == "EXITO"
    ]

    rechazados = [
        r for r in registros
        if r["estado"] == "RECHAZO"
    ]

    errores = [
        r for r in registros
        if r["estado"] == "ERROR"
    ]

    folios = [r["folio"] for r in exitosos]

    duplicados = len(folios) - len(set(folios))

    promedio = sum(
        r["latencia_ms"] for r in registros
    ) / len(registros)

    # Guardar evidencia para el reporte
    carpeta = Path(__file__).parent / "resultados_demo_web"
    carpeta.mkdir(exist_ok=True)

    fecha = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    archivo = carpeta / f"{modo}_{fecha}.csv"

    columnas = [
        "hilo_id",
        "hora_envio",
        "hora_respuesta",
        "latencia_ms",
        "folio",
        "estado",
        "http"
    ]

    with archivo.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        escritor = csv.DictWriter(
            f,
            fieldnames=columnas
        )

        escritor.writeheader()
        escritor.writerows(registros)

    return {
        "modo": modo,
        "aforo": AFORO,
        "solicitudes": TOTAL,
        "aceptados": len(exitosos),
        "rechazados": len(rechazados),
        "errores": len(errores),
        "duplicados": duplicados,
        "contador_final": prueba.emitidos,
        "duracion_s": round(duracion, 3),
        "latencia_promedio_ms": round(promedio, 2),
        "boletos_por_segundo": round(
            len(exitosos) / duracion, 2
        ),
        "archivo_csv": str(archivo),
        "registros": registros
    }

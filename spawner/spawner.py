
import argparse
import csv
import queue
import threading
import time
import uuid

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests


CAMPOS = [
    "hilo_id",
    "solicitud_id",
    "hora_envio",
    "hora_respuesta",
    "latencia_ms",
    "folio",
    "estado",
    "http",
    "detalle"
]


def ahora():
    return datetime.now().astimezone().isoformat(
        timespec="milliseconds"
    )


# =====================================
# CONSUMIDOR: GUARDAR BITÁCORA
# =====================================

def consumidor(resultados, archivo):

    with open(
        archivo,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        escritor = csv.DictWriter(
            f,
            fieldnames=CAMPOS
        )

        escritor.writeheader()

        while True:
            resultado = resultados.get()

            if resultado is None:
                resultados.task_done()
                break

            escritor.writerow(resultado)
            f.flush()

            resultados.task_done()


# =====================================
# PRODUCTOR: HILO SOLICITANTE
# =====================================

def solicitar(
    numero,
    url,
    semaforo,
    barrera,
    resultados,
    timeout
):

    hilo_id = f"spawner-{numero:03d}"
    solicitud_id = str(uuid.uuid4())

    registro = {
        "hilo_id": hilo_id,
        "solicitud_id": solicitud_id,
        "hora_envio": "",
        "hora_respuesta": "",
        "latencia_ms": 0,
        "folio": "",
        "estado": "ERROR",
        "http": "",
        "detalle": ""
    }

    try:
        # Barrera para iniciar juntos en modo ráfaga
        if barrera is not None:
            if numero <= barrera.parties:
                barrera.wait(timeout=30)

        # Máximo de solicitudes simultáneas
        with semaforo:

            registro["hora_envio"] = ahora()
            inicio = time.perf_counter()

            try:
                respuesta = requests.post(
                    url,
                    json={
                        "solicitud_id": solicitud_id,
                        "hilo_id": hilo_id
                    },
                    timeout=timeout
                )

                registro["http"] = respuesta.status_code

                datos = respuesta.json()

                if respuesta.status_code in (200, 201):
                    if (
                        datos.get("estado") == "EXITO"
                        and datos.get("folio")
                    ):
                        registro["estado"] = "EXITO"
                        registro["folio"] = datos["folio"]
                        registro["detalle"] = "Boleto emitido"
                    else:
                        registro["detalle"] = (
                            "Respuesta inesperada del servidor"
                        )

                elif respuesta.status_code == 409:
                    registro["estado"] = "RECHAZO"
                    registro["detalle"] = "Aforo agotado"

                else:
                    registro["detalle"] = str(
                        datos.get("detail", "Error HTTP")
                    )

            except requests.exceptions.Timeout:
                registro["detalle"] = "Timeout de red"

            except requests.exceptions.ConnectionError:
                registro["detalle"] = "Error de conexión"

            except requests.exceptions.RequestException as e:
                registro["detalle"] = str(e)

            except ValueError:
                registro["detalle"] = "Respuesta JSON inválida"

            finally:
                registro["hora_respuesta"] = ahora()
                registro["latencia_ms"] = round(
                    (time.perf_counter() - inicio) * 1000,
                    2
                )

    except threading.BrokenBarrierError:
        registro["detalle"] = "Error de sincronización de barrera"
        registro["hora_envio"] = ahora()
        registro["hora_respuesta"] = ahora()

    resultados.put(registro)
    return registro


# =====================================
# COORDINADOR DEL EXPERIMENTO
# =====================================

def ejecutar(config):

    total = config.solicitudes
    hilos = min(config.hilos, total)

    semaforo = threading.Semaphore(
        config.concurrentes
    )

    barrera = None

    if config.modo == "rafaga":
        barrera = threading.Barrier(hilos)

    resultados = queue.Queue()

    carpeta = Path(__file__).resolve().parent / "resultados"
    carpeta.mkdir(exist_ok=True)

    nombre = datetime.now().strftime(
        "bitacora_%Y%m%d_%H%M%S.csv"
    )

    archivo = carpeta / nombre

    hilo_consumidor = threading.Thread(
        target=consumidor,
        args=(resultados, archivo),
        name="consumidor"
    )

    hilo_consumidor.start()

    url = config.url.rstrip("/") + "/boletos"

    print("\n--- AUDITORIO PLATA: SPAWNER ---")
    print("Solicitudes:", total)
    print("Hilos:", hilos)
    print("Simultáneas máximas:", config.concurrentes)
    print("Modo:", config.modo)
    print("Servidor:", url)

    inicio_global = time.perf_counter()

    registros = []

    with ThreadPoolExecutor(
        max_workers=hilos
    ) as pool:

        tareas = []

        # Reservamos 10 segundos de margen
        duracion_envio = max(
            0,
            config.ventana - 10
        )

        for i in range(total):

            if config.modo == "uniforme":

                objetivo = (
                    inicio_global
                    + i * duracion_envio / total
                )

                espera = objetivo - time.perf_counter()

                if espera > 0:
                    time.sleep(espera)

            tarea = pool.submit(
                solicitar,
                i + 1,
                url,
                semaforo,
                barrera,
                resultados,
                config.timeout
            )

            tareas.append(tarea)

        for tarea in tareas:
            registros.append(tarea.result())

    duracion = time.perf_counter() - inicio_global

    # Finalizar el consumidor
    resultados.put(None)
    resultados.join()
    hilo_consumidor.join()

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

    promedio = (
        sum(r["latencia_ms"] for r in registros)
        / len(registros)
    )

    tasa = len(exitosos) / duracion

    print("\n--- RESULTADOS ---")
    print("Exitosos:", len(exitosos))
    print("Rechazados:", len(rechazados))
    print("Errores:", len(errores))
    print("Folios duplicados:", duplicados)
    print(f"Tiempo total: {duracion:.2f} s")
    print(f"Respuesta promedio: {promedio:.2f} ms")
    print(f"Rendimiento: {tasa:.2f} boletos/s")
    print("Bitácora:", archivo)

    if len(exitosos) == total and duracion <= config.ventana:
        print("META CUMPLIDA")
    else:
        print("META NO CUMPLIDA")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000"
    )

    parser.add_argument(
        "--solicitudes",
        type=int,
        default=100
    )

    parser.add_argument(
        "--hilos",
        type=int,
        default=100
    )

    parser.add_argument(
        "--concurrentes",
        type=int,
        default=10
    )

    parser.add_argument(
        "--modo",
        choices=["uniforme", "rafaga"],
        default="uniforme"
    )

    parser.add_argument(
        "--ventana",
        type=float,
        default=60
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=15
    )

    args = parser.parse_args()

    if (
        args.solicitudes < 1
        or args.hilos < 1
        or args.concurrentes < 1
        or args.ventana <= 0
        or args.timeout <= 0
    ):
        parser.error(
            "Los parámetros numéricos deben ser positivos"
        )

    ejecutar(args)

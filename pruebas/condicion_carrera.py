
import threading
from concurrent.futures import ThreadPoolExecutor

from servidor.readers_writers import ReadersWriters


SOLICITUDES = 10
AFORO = 3


# ======================================
# EXPERIMENTO 1: SIN SINCRONIZACIÓN
# ======================================

class AuditorioInseguro:

    def __init__(self):
        self.aforo = AFORO
        self.emitidos = 0
        self.folios = []

    def solicitar(self, barrera):

        # Lectura del recurso compartido
        ocupados = self.emitidos

        if ocupados >= self.aforo:
            return None

        # Forzamos a los hilos a leer el mismo
        # valor antes de permitir la escritura.
        barrera.wait()

        # SECCIÓN CRÍTICA SIN PROTECCIÓN
        numero = ocupados + 1
        folio = f"AP-{numero:06d}"

        self.emitidos = numero
        self.folios.append(folio)

        return folio


# ======================================
# EXPERIMENTO 2: CON READERS-WRITERS
# ======================================

class AuditorioSeguro:

    def __init__(self):
        self.aforo = AFORO
        self.emitidos = 0
        self.folios = []

        self.rw = ReadersWriters()

    def solicitar(self, barrera):

        # Todos intentan comenzar al mismo tiempo
        barrera.wait()

        # SECCIÓN CRÍTICA PROTEGIDA
        with self.rw.escritor():

            if self.emitidos >= self.aforo:
                return None

            numero = self.emitidos + 1
            folio = f"AP-{numero:06d}"

            self.emitidos = numero
            self.folios.append(folio)

            return folio


# ======================================
# EJECUCIÓN DE EXPERIMENTOS
# ======================================

def ejecutar(auditorio, nombre):

    barrera = threading.Barrier(SOLICITUDES)

    with ThreadPoolExecutor(
        max_workers=SOLICITUDES
    ) as pool:

        tareas = [
            pool.submit(auditorio.solicitar, barrera)
            for _ in range(SOLICITUDES)
        ]

        resultados = [
            tarea.result() for tarea in tareas
        ]

    aceptados = [
        folio for folio in resultados
        if folio is not None
    ]

    rechazados = len(resultados) - len(aceptados)

    duplicados = (
        len(aceptados) - len(set(aceptados))
    )

    print(f"\n--- {nombre} ---")
    print("Aforo máximo:", auditorio.aforo)
    print("Solicitudes:", SOLICITUDES)
    print("Boletos aceptados:", len(aceptados))
    print("Boletos rechazados:", rechazados)
    print("Folios duplicados:", duplicados)
    print("Contador emitidos:", auditorio.emitidos)
    print("Folios:", aceptados)

    return len(aceptados), duplicados


if __name__ == "__main__":

    # Prueba sin protección
    inseguro = AuditorioInseguro()

    aceptados1, duplicados1 = ejecutar(
        inseguro,
        "SIN SINCRONIZACIÓN"
    )

    # Prueba con protección
    seguro = AuditorioSeguro()

    aceptados2, duplicados2 = ejecutar(
        seguro,
        "CON READERS-WRITERS"
    )

    assert aceptados1 > AFORO
    assert duplicados1 > 0

    assert aceptados2 == AFORO
    assert duplicados2 == 0

    print("\nCOMPARACIÓN COMPLETADA")

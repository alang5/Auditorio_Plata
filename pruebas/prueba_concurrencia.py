
import time
from concurrent.futures import ThreadPoolExecutor

from servidor.readers_writers import ReadersWriters


class Auditorio:

    def __init__(self, aforo=20000):

        self.aforo = aforo
        self.emitidos = 0
        self.folios = []

        self.rw = ReadersWriters()

    def consultar_aforo(self):

        with self.rw.lector():

            disponibles = self.aforo - self.emitidos

            # Simulamos el tiempo de lectura
            time.sleep(0.02)

            return disponibles

    def emitir_boleto(self):

        with self.rw.escritor():

            if self.emitidos >= self.aforo:
                return None

            # Generamos un folio provisional
            numero = self.emitidos + 1
            folio = f"AP-{numero:06d}"

            # Simulamos una operación de escritura
            time.sleep(0.002)

            self.emitidos = numero
            self.folios.append(folio)

            return folio


# --------------------------------
# PRUEBA 1: 100 BOLETOS
# --------------------------------

auditorio = Auditorio(20000)

inicio = time.perf_counter()

with ThreadPoolExecutor(max_workers=20) as pool:

    lectores = [
        pool.submit(auditorio.consultar_aforo)
        for _ in range(10)
    ]

    escritores = [
        pool.submit(auditorio.emitir_boleto)
        for _ in range(100)
    ]

    consultas = [t.result() for t in lectores]
    folios = [t.result() for t in escritores]

duracion = time.perf_counter() - inicio

exitosos = [f for f in folios if f is not None]

print("\n--- AUDITORIO PLATA ---")
print("Aforo:", auditorio.aforo)
print("Boletos emitidos:", auditorio.emitidos)
print("Disponibles:", auditorio.consultar_aforo())
print("Folios únicos:", len(set(exitosos)))
print("Lectores simultáneos máximos:",
      auditorio.rw.max_lectores)
print(f"Tiempo total: {duracion:.3f} segundos")

assert len(exitosos) == 100
assert len(set(exitosos)) == 100

print("PRUEBA 1: CORRECTA")


# --------------------------------
# PRUEBA 2: AFORO LIMITADO
# --------------------------------

auditorio_pequeno = Auditorio(3)

with ThreadPoolExecutor(max_workers=10) as pool:

    resultados = list(
        pool.map(
            lambda _: auditorio_pequeno.emitir_boleto(),
            range(10)
        )
    )

aceptados = sum(f is not None for f in resultados)
rechazados = sum(f is None for f in resultados)

print("\n--- PRUEBA DE AFORO ---")
print("Aforo máximo:", auditorio_pequeno.aforo)
print("Solicitudes:", len(resultados))
print("Aceptados:", aceptados)
print("Rechazados:", rechazados)

assert aceptados == 3
assert rechazados == 7

print("PRUEBA 2: CORRECTA")

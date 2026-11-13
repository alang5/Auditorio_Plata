
import threading
from contextlib import contextmanager


class ReadersWriters:

    def __init__(self):

        # Semáforo para controlar escritores y lectores
        self.rw_mutex = threading.Semaphore(1)

        # Semáforo que protege read_count
        self.mutex = threading.Semaphore(1)

        # Número de lectores activos
        self.read_count = 0

        # Variable para nuestras pruebas
        self.max_lectores = 0

    @contextmanager
    def lector(self):

        # Entrada de lectores
        with self.mutex:

            self.read_count += 1

            if self.read_count == 1:
                self.rw_mutex.acquire()

            self.max_lectores = max(
                self.max_lectores,
                self.read_count
            )

        try:
            # Sección de lectura
            yield

        finally:
            # Salida de lectores
            with self.mutex:

                self.read_count -= 1

                if self.read_count == 0:
                    self.rw_mutex.release()

    @contextmanager
    def escritor(self):

        # Solo un escritor puede ingresar
        with self.rw_mutex:

            # Sección crítica de escritura
            yield

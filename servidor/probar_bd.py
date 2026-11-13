from servidor.database import conectar


def main():
    print("Conectando con Oracle...")

    with conectar() as conexion:
        with conexion.cursor() as cursor:

            cursor.execute("""
                SELECT nombre, aforo, emitidos
                FROM eventos
                WHERE id = 1
            """)

            evento = cursor.fetchone()

            if evento is None:
                print("No se encontró el concierto.")
                return

            nombre, aforo, emitidos = evento

            print("\n--- AUDITORIO PLATA ---")
            print("Evento:", nombre)
            print("Aforo:", aforo)
            print("Boletos emitidos:", emitidos)
            print("Disponibles:", aforo - emitidos)

    print("\nConexión exitosa.")


if __name__ == "__main__":
    main()
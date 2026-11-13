
import os
from pathlib import Path

import oracledb
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def conectar():

    usuario = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASSWORD")
    dsn = os.getenv("ORACLE_DSN")

    if not all([usuario, password, dsn]):
        raise RuntimeError(
            "Faltan datos de conexión en .env"
        )

    conexion = oracledb.connect(
        user=usuario,
        password=password,
        dsn=dsn
    )

    return conexion

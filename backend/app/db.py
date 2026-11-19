import json
import sqlite3
from datetime import datetime, timezone

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS velas_procesadas (fecha_vela TEXT PRIMARY KEY, cierre REAL NOT NULL, procesada_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisiones (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_vela TEXT NOT NULL, pronostico REAL, senal TEXT,
    accion_llm TEXT, justificacion TEXT, latencia_llm REAL, accion_final TEXT NOT NULL, motivo_riesgo TEXT, creada_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ordenes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_vela TEXT NOT NULL, lado TEXT NOT NULL,
    precio REAL NOT NULL, cantidad REAL NOT NULL, costo REAL NOT NULL, estado TEXT NOT NULL, creada_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS patrimonio (fecha_vela TEXT PRIMARY KEY, efectivo REAL NOT NULL, btc REAL NOT NULL, precio REAL NOT NULL, total REAL NOT NULL);
CREATE TABLE IF NOT EXISTS errores (id INTEGER PRIMARY KEY AUTOINCREMENT, etapa TEXT NOT NULL, mensaje TEXT NOT NULL, creado_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
"""


def ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def conectar():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    return con


def leer_estado(con):
    fila = con.execute("SELECT valor FROM estado WHERE clave='cartera'").fetchone()
    if fila:
        return json.loads(fila["valor"])
    return {"efectivo": config.CAPITAL_INICIAL, "btc": 0.0, "modo": "detenido"}


def guardar_estado(con, cartera):
    con.execute("INSERT INTO estado VALUES ('cartera', ?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor", (json.dumps(cartera),))


def registrar_error(con, etapa, mensaje):
    con.execute("INSERT INTO errores (etapa, mensaje, creado_utc) VALUES (?,?,?)", (etapa, str(mensaje)[:500], ahora()))
    con.commit()

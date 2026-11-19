import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")


def _num(nombre, defecto):
    return float(os.getenv(nombre, defecto))


API_KEY = os.getenv("BOT_API_KEY", "")
SIMBOLO = os.getenv("SIMBOLO", "BTCUSDT")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODELO = os.getenv("OLLAMA_MODELO", "llama3.2:3b")
DB_PATH = Path(os.getenv("DB_PATH", RAIZ / "data" / "bot.db"))

CAPITAL_INICIAL = _num("CAPITAL_INICIAL", 50_000)
COSTO = _num("COSTO", 0.0)
EXPOSICION_MAX = _num("EXPOSICION_MAX", 1.0)
PERDIDA_DIARIA_MAX = _num("PERDIDA_DIARIA_MAX", 0.05)
ANTIGUEDAD_MAX_HORAS = _num("ANTIGUEDAD_MAX_HORAS", 36)
UMBRAL = _num("UMBRAL", 0.0)
INTERVALO_SEGUNDOS = int(_num("INTERVALO_SEGUNDOS", 300))
VERSION = "0.0.1"

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import pandas as pd

URL = "https://api.mexc.com/api/v3/klines"


class DatosInvalidos(Exception):
    pass


def _get(url, intentos=3):
    for intento in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "bot-trading-btc"}), timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or intento == intentos:
                raise DatosInvalidos(f"MEXC respondió {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if intento == intentos:
                raise DatosInvalidos(f"MEXC sin respuesta: {exc}") from exc
        time.sleep(2 ** intento)


def velas_cerradas(simbolo, dias=900):
    ahora = datetime.now(timezone.utc)
    inicio, velas = ahora - timedelta(days=dias), {}
    while inicio < ahora:
        fin = min(inicio + timedelta(days=450), ahora)
        for v in _get(f"{URL}?symbol={simbolo}&interval=1d&startTime={int(inicio.timestamp() * 1000)}&endTime={int(fin.timestamp() * 1000)}&limit=500"):
            velas[v[0]] = v
        inicio = fin
    if not velas:
        raise DatosInvalidos(f"MEXC no devolvió velas para {simbolo}")
    df = pd.DataFrame([velas[k] for k in sorted(velas)],
                      columns=["open_time", "open", "high", "low", "close", "volume", "close_time", "volume_quote"])
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
    df = df[df.close_time < ahora.timestamp() * 1000]
    df = df[df.open_time % 86_400_000 == 0]
    if (df[["open", "high", "low", "close"]] <= 0).any().any() or df.open_time.duplicated().any():
        raise DatosInvalidos("Velas con precios no positivos o fechas duplicadas")
    if (df.open_time.diff().dropna() != 86_400_000).any():
        raise DatosInvalidos("Hay huecos en el calendario diario")
    df["fecha"] = pd.to_datetime(df.open_time, unit="ms", utc=True)
    return df.reset_index(drop=True)

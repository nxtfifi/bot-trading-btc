import json
import time
import urllib.error
import urllib.request

from . import config

ACCIONES = {"comprar", "mantener", "vender"}


class LLMNoDisponible(Exception):
    pass


def proponer(datos):
    prompt = (
        "Eres el asistente de un bot de trading en papel. Con los datos siguientes propone UNA acción: "
        "comprar, mantener o vender (vender solo cierra una posición existente; no hay cortos ni apalancamiento). "
        "Responde solo JSON con las claves accion, simbolo, fecha_vela y justificacion (máximo 25 palabras, basada en los datos).\n"
        + json.dumps(datos, ensure_ascii=False)
    )
    cuerpo = json.dumps({"model": config.OLLAMA_MODELO, "prompt": prompt, "format": "json", "stream": False}).encode()
    t0 = time.time()
    try:
        req = urllib.request.Request(f"{config.OLLAMA_URL}/api/generate", data=cuerpo, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            texto = json.load(r)["response"]
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        raise LLMNoDisponible(f"Ollama no respondió en {config.OLLAMA_URL}: {exc}") from exc
    latencia = round(time.time() - t0, 2)
    try:
        propuesta = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ValueError(f"El LLM no devolvió JSON válido: {texto[:120]}") from exc
    if propuesta.get("accion") not in ACCIONES:
        raise ValueError(f"Acción no permitida: {propuesta.get('accion')}")
    if propuesta.get("simbolo") != datos["simbolo"] or propuesta.get("fecha_vela") != datos["fecha_vela"]:
        raise ValueError("El LLM respondió con otro símbolo o fecha de vela")
    return {"accion": propuesta["accion"], "justificacion": str(propuesta.get("justificacion", ""))[:200], "latencia_s": latencia}

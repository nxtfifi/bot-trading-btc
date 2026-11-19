from datetime import datetime, timezone

from . import config, db, llm, mexc, modelo


def evaluar_riesgo(accion, cartera, precio, fecha_vela, total_ayer):
    edad_h = (datetime.now(timezone.utc) - fecha_vela).total_seconds() / 3600 - 24
    if edad_h > config.ANTIGUEDAD_MAX_HORAS:
        return "mantener", f"dato atrasado ({edad_h:.0f} h desde el cierre)"
    total = cartera["efectivo"] + cartera["btc"] * precio
    if total_ayer and (total / total_ayer - 1) < -config.PERDIDA_DIARIA_MAX:
        return "mantener", "pérdida diaria máxima alcanzada; nuevas órdenes bloqueadas"
    if accion == "comprar" and cartera["btc"] > 0:
        return "mantener", "ya hay posición abierta"
    if accion == "comprar" and cartera["efectivo"] <= 0:
        return "mantener", "saldo insuficiente"
    if accion == "vender" and cartera["btc"] <= 0:
        return "mantener", "no hay posición que vender"
    return accion, "aprobada"


def ejecutar_paper(con, accion, cartera, precio, fecha):
    if accion == "comprar":
        monto = cartera["efectivo"] * config.EXPOSICION_MAX
        costo = monto * config.COSTO
        cantidad = round((monto - costo) / precio, 6)
        cartera["efectivo"] -= cantidad * precio + costo
        cartera["btc"] += cantidad
    elif accion == "vender":
        cantidad = cartera["btc"]
        costo = cantidad * precio * config.COSTO
        cartera["efectivo"] += cantidad * precio - costo
        cartera["btc"] = 0.0
    else:
        return
    con.execute("INSERT INTO ordenes (fecha_vela, lado, precio, cantidad, costo, estado, creada_utc) VALUES (?,?,?,?,?,?,?)",
                (fecha, accion, precio, cantidad, costo, "ejecutada_paper", db.ahora()))


def correr_ciclo(con):
    cartera = db.leer_estado(con)
    if cartera["modo"] == "detenido":
        return {"resultado": "detenido", "mensaje": "el bot está detenido; no se generan órdenes"}
    try:
        velas = mexc.velas_cerradas(config.SIMBOLO)
    except mexc.DatosInvalidos as exc:
        db.registrar_error(con, "datos", exc)
        cartera["modo"] = "pausado"
        db.guardar_estado(con, cartera)
        con.commit()
        return {"resultado": "pausado", "mensaje": f"datos no válidos: {exc}"}
    ultima = velas.iloc[-1]
    fecha = ultima.fecha.strftime("%Y-%m-%d")
    if con.execute("SELECT 1 FROM velas_procesadas WHERE fecha_vela=?", (fecha,)).fetchone():
        return {"resultado": "sin_cambios", "mensaje": f"la vela {fecha} ya se procesó"}

    pronostico, n = modelo.pronosticar(velas)
    ind = modelo.indicadores(velas).iloc[-1]
    precio = float(ultima.close)
    senal = "comprar" if pronostico > config.UMBRAL else "vender"
    datos = {"simbolo": config.SIMBOLO, "fecha_vela": fecha, "cierre": precio, "pronostico_rendimiento": round(pronostico, 6),
             "senal_modelo": senal, "distancia_sma20": round(float(ind.distancia_sma20), 4), "volatilidad20": round(float(ind.volatilidad20), 4),
             "posicion_btc": cartera["btc"], "efectivo_usdt": round(cartera["efectivo"], 2)}
    accion_llm, justificacion, latencia = None, None, None
    try:
        propuesta = llm.proponer(datos)
        accion_llm, justificacion, latencia = propuesta["accion"], propuesta["justificacion"], propuesta["latencia_s"]
        propuesta_final = accion_llm
    except (llm.LLMNoDisponible, ValueError) as exc:
        db.registrar_error(con, "llm", exc)
        propuesta_final = senal
        justificacion = "LLM no disponible o respuesta inválida; se usa la señal del modelo"

    previo = con.execute("SELECT total FROM patrimonio ORDER BY fecha_vela DESC LIMIT 1").fetchone()
    accion_final, motivo = evaluar_riesgo(propuesta_final, cartera, precio, ultima.fecha, previo["total"] if previo else None)
    if cartera["modo"] == "pausado":
        accion_final, motivo = "mantener", "bot en pausa"
    ejecutar_paper(con, accion_final, cartera, precio, fecha)
    total = cartera["efectivo"] + cartera["btc"] * precio
    con.execute("INSERT INTO decisiones (fecha_vela, pronostico, senal, accion_llm, justificacion, latencia_llm, accion_final, motivo_riesgo, creada_utc) VALUES (?,?,?,?,?,?,?,?,?)",
                (fecha, pronostico, senal, accion_llm, justificacion, latencia, accion_final, motivo, db.ahora()))
    con.execute("INSERT INTO patrimonio VALUES (?,?,?,?,?) ON CONFLICT(fecha_vela) DO NOTHING", (fecha, cartera["efectivo"], cartera["btc"], precio, total))
    con.execute("INSERT INTO velas_procesadas VALUES (?,?,?)", (fecha, precio, db.ahora()))
    db.guardar_estado(con, cartera)
    con.commit()
    return {"resultado": "procesada", "fecha_vela": fecha, "pronostico": pronostico, "senal": senal, "accion_llm": accion_llm,
            "accion_final": accion_final, "motivo": motivo, "patrimonio": total, "ejemplos_entrenamiento": n}

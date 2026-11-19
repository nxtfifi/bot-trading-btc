import asyncio
import hmac
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException

from . import ciclo, config, db, modelo


def requiere_clave(x_api_key: str = Header(default="")):
    if not config.API_KEY or not hmac.compare_digest(x_api_key, config.API_KEY):
        raise HTTPException(status_code=401, detail="Clave de API ausente o incorrecta")


async def bucle():
    while True:
        con = db.conectar()
        try:
            if db.leer_estado(con)["modo"] == "activo":
                await asyncio.to_thread(ciclo.correr_ciclo, con)
        except Exception as exc:
            db.registrar_error(con, "ciclo", exc)
        finally:
            con.close()
        await asyncio.sleep(config.INTERVALO_SEGUNDOS)


@asynccontextmanager
async def vida(app):
    if not config.API_KEY:
        raise RuntimeError("Falta BOT_API_KEY en backend/.env (copie .env.example)")
    tarea = asyncio.create_task(bucle())
    yield
    tarea.cancel()


app = FastAPI(title="Bot de trading BTC/USDT (paper)", version=config.VERSION, lifespan=vida)


@app.get("/salud")
def salud():
    return {"ok": True, "version": config.VERSION}


@app.get("/estado", dependencies=[Depends(requiere_clave)])
def estado():
    con = db.conectar()
    cartera = db.leer_estado(con)
    ultima = con.execute("SELECT * FROM decisiones ORDER BY id DESC LIMIT 1").fetchone()
    patrimonio = [dict(r) for r in con.execute("SELECT * FROM patrimonio ORDER BY fecha_vela")]
    errores = [dict(r) for r in con.execute("SELECT * FROM errores ORDER BY id DESC LIMIT 5")]
    con.close()
    return {"version": config.VERSION, "simbolo": config.SIMBOLO, "modelo": modelo.CONTRATO["version"], "cartera": cartera,
            "ultima_decision": dict(ultima) if ultima else None, "patrimonio": patrimonio, "errores": errores,
            "limites": {"exposicion_max": config.EXPOSICION_MAX, "perdida_diaria_max": config.PERDIDA_DIARIA_MAX,
                        "antiguedad_max_horas": config.ANTIGUEDAD_MAX_HORAS, "costo": config.COSTO}}


@app.post("/control/{accion}", dependencies=[Depends(requiere_clave)])
def control(accion: str):
    modos = {"iniciar": "activo", "pausar": "pausado", "detener": "detenido"}
    if accion not in modos:
        raise HTTPException(status_code=400, detail="Acción no válida: use iniciar, pausar o detener")
    con = db.conectar()
    cartera = db.leer_estado(con)
    cartera["modo"] = modos[accion]
    db.guardar_estado(con, cartera)
    con.commit()
    con.close()
    return {"modo": cartera["modo"]}


@app.post("/ciclo", dependencies=[Depends(requiere_clave)])
def ciclo_manual():
    con = db.conectar()
    try:
        return ciclo.correr_ciclo(con)
    finally:
        con.close()

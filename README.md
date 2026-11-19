# Bot de trading BTC/USDT — v0.0.1

Bot financiero de **paper trading** para BTC/USDT en velas diarias. Toma los datos públicos de MEXC, pronostica el rendimiento del día siguiente con un modelo de regresión y le pide una propuesta de acción a un **LLM local (Ollama)**. Antes de simular cualquier orden, una capa de riesgo determinista revisa esa propuesta.

> Versión actual: **0.0.1**. Es el primer entregable del BOT. No envía órdenes reales a ningún exchange.

Autor: Felix García · Ciencia de Datos Aplicada a la Economía, IBERO León.

## Tecnologías en uso

| Capa | Tecnología | Uso |
|---|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn | API del bot y ciclo automático |
| Datos | API pública spot de MEXC (`/api/v3/klines`) | Velas diarias cerradas BTCUSDT |
| Modelo | pandas, NumPy, scikit-learn | Regresión lineal con 20 rezagos de rendimiento (modelo elegido en el capítulo 8) |
| IA | Ollama (LLM local, `llama3.2:3b`) | Propone comprar / mantener / vender con justificación |
| Persistencia | SQLite | Decisiones, órdenes simuladas, patrimonio y errores |
| UI | Vue 3, Vite, TypeScript | Panel de estado y controles |
| Configuración | python-dotenv | Secretos y parámetros en `backend/.env` |

## Cómo funciona un ciclo

1. **Datos.** Descarga unas 900 velas diarias **cerradas** de MEXC y las valida: precios positivos, sin duplicados y sin huecos. Si los datos no sirven, el bot se pausa y registra el error.
2. **Modelo.** Entrena la regresión lineal con todo el histórico etiquetado y pronostica el rendimiento de la siguiente vela. Si el pronóstico es mayor que `UMBRAL`, la señal es comprar; si no, vender.
3. **LLM local.** Ollama recibe solo datos de mercado y de cartera (precio, pronóstico, SMA20, volatilidad, posición). Su respuesta se valida: la acción tiene que estar en la lista blanca y el símbolo y la fecha tienen que coincidir. Si el LLM no responde o contesta algo inválido, se usa la señal del modelo y se registra el error.
4. **Riesgo.** Bloquea la orden en cualquiera de estos casos:
   - el dato está atrasado;
   - ya se alcanzó la pérdida diaria máxima;
   - ya hay una posición abierta;
   - no hay saldo;
   - se intenta vender sin posición.

   No hay apalancamiento ni posiciones cortas.
5. **Paper.** Simula la orden con $50,000 USDT iniciales y guarda la decisión y el patrimonio. Cada vela se procesa **una sola vez** (idempotente).

## Seguridad

- **No se le pasan claves a la IA.** El prompt del LLM solo lleva datos de mercado y de cartera. El LLM corre en local, así que nada sale a servicios externos.
- La clave del bot (`BOT_API_KEY`) solo vive en `backend/.env`, que está en `.gitignore`. El repo incluye únicamente `backend/.env.example`, sin valores reales.
- Todos los endpoints, salvo `/salud`, piden el encabezado `X-API-Key`, que se compara en tiempo constante.
- La UI no guarda la clave. El proxy de Vite la lee de `backend/.env` del lado del servidor y la agrega a cada petición, así que no aparece en el bundle del navegador ni en variables `VITE_`.
- Solo paper trading: no hay ningún código que envíe órdenes reales a MEXC.

## Estructura

```
backend/
  app/
    config.py   parámetros desde .env
    mexc.py     descarga y validación de velas
    modelo.py   regresión lineal 20 rezagos + indicadores
    llm.py      cliente Ollama con validación de respuesta
    ciclo.py    datos → modelo → LLM → riesgo → paper
    db.py       esquema SQLite
    main.py     API FastAPI y bucle automático
  requirements.txt
  .env.example
frontend/       Vue 3 + Vite + TypeScript
```

## Cómo correrlo

```bash
# 1. Backend
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # y cambia BOT_API_KEY por una clave larga
uvicorn app.main:app --port 8000

# 2. LLM local (opcional en v0.0.1; sin él se usa la señal del modelo)
ollama pull llama3.2:3b

# 3. UI
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

API:

| Método | Ruta | Para qué sirve |
|---|---|---|
| GET | `/salud` | Ver si el bot responde y qué versión corre |
| GET | `/estado` | Cartera, última decisión, patrimonio y errores |
| POST | `/control/iniciar` · `/pausar` · `/detener` | Cambiar el modo del bot |
| POST | `/ciclo` | Correr un ciclo manual |

## Historial de commits / versiones

| Versión | Commit | Qué incluye | Tecnologías |
|---|---|---|---|
| 0.0.1 | `chore: estructura inicial del bot` | Carpetas, `.gitignore`, dependencias, `.env.example` | Git, Python |
| 0.0.1 | `feat: datos de MEXC y modelo lineal de 20 rezagos` | Descarga paginada de velas cerradas, validación y pronóstico | MEXC API, pandas, scikit-learn |
| 0.0.1 | `feat: ciclo paper con riesgo, LLM local y API` | Motor paper, controles de riesgo, cliente Ollama, SQLite, endpoints con clave | FastAPI, SQLite, Ollama |
| 0.0.1 | `feat: panel en Vue + Vite + TypeScript` | Panel de estado y botones iniciar/pausar/detener/ciclo, proxy con la clave del lado del servidor | Vue 3, Vite, TypeScript |
| 0.0.1 | `docs: README de la versión 0.0.1` | Este documento | Markdown |

## Pendiente para las siguientes versiones

- Instalar y probar Ollama en la máquina del bot (en v0.0.1 se probó el respaldo cuando el LLM no está disponible).
- Cambiar al modelo de deep learning de los avances del equipo (MLP/LSTM) cuando le gane al lineal fuera de muestra.
- Correr el bot en la cuenta demo de MEXC y medir el rendimiento contra la meta de +20%.

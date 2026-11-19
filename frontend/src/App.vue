<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

interface Decision {
  fecha_vela: string
  pronostico: number
  senal: string
  accion_llm: string | null
  justificacion: string | null
  accion_final: string
  motivo_riesgo: string
}
interface Punto { fecha_vela: string; efectivo: number; btc: number; precio: number; total: number }
interface Estado {
  version: string
  simbolo: string
  modelo: string
  cartera: { efectivo: number; btc: number; modo: string }
  ultima_decision: Decision | null
  patrimonio: Punto[]
  errores: { etapa: string; mensaje: string; creado_utc?: string }[]
}

const estado = ref<Estado | null>(null)
const error = ref('')
const ocupado = ref(false)
let timer: number | undefined

async function cargar() {
  try {
    const r = await fetch('/api/estado')
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    estado.value = await r.json()
    error.value = ''
  } catch (e) {
    error.value = `No se pudo leer el estado del backend (${(e as Error).message})`
  }
}

async function enviar(ruta: string) {
  ocupado.value = true
  try {
    const r = await fetch(`/api${ruta}`, { method: 'POST' })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    await cargar()
  } catch (e) {
    error.value = `Falló ${ruta}: ${(e as Error).message}`
  } finally {
    ocupado.value = false
  }
}

const ultimo = computed(() => estado.value?.patrimonio.at(-1))
const total = computed(() => ultimo.value?.total ?? estado.value?.cartera.efectivo ?? 0)
const usd = (n: number) => n.toLocaleString('es-MX', { style: 'currency', currency: 'USD' })

onMounted(() => {
  cargar()
  timer = window.setInterval(cargar, 15000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <main>
    <header>
      <h1>Bot BTC/USDT <small>v{{ estado?.version ?? '—' }} · paper trading</small></h1>
      <span class="modo" :data-modo="estado?.cartera.modo">{{ estado?.cartera.modo ?? '...' }}</span>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <section class="controles">
      <button :disabled="ocupado" @click="enviar('/control/iniciar')">Iniciar</button>
      <button :disabled="ocupado" @click="enviar('/control/pausar')">Pausar</button>
      <button :disabled="ocupado" @click="enviar('/control/detener')">Detener</button>
      <button :disabled="ocupado" @click="enviar('/ciclo')">Correr ciclo ahora</button>
    </section>

    <section v-if="estado" class="tarjetas">
      <div><h2>Patrimonio</h2><p>{{ usd(total) }}</p></div>
      <div><h2>Efectivo</h2><p>{{ usd(estado.cartera.efectivo) }}</p></div>
      <div><h2>Posición BTC</h2><p>{{ estado.cartera.btc.toFixed(6) }}</p></div>
      <div><h2>Último cierre</h2><p>{{ ultimo ? usd(ultimo.precio) : '—' }}</p></div>
    </section>

    <section v-if="estado?.ultima_decision" class="decision">
      <h2>Última decisión · vela {{ estado.ultima_decision.fecha_vela }}</h2>
      <dl>
        <dt>Modelo</dt><dd>{{ estado.modelo }}</dd>
        <dt>Pronóstico</dt><dd>{{ (estado.ultima_decision.pronostico * 100).toFixed(3) }} %</dd>
        <dt>Señal del modelo</dt><dd>{{ estado.ultima_decision.senal }}</dd>
        <dt>Propuesta LLM</dt><dd>{{ estado.ultima_decision.accion_llm ?? 'sin LLM' }}</dd>
        <dt>Justificación</dt><dd>{{ estado.ultima_decision.justificacion }}</dd>
        <dt>Acción final</dt><dd><strong>{{ estado.ultima_decision.accion_final }}</strong></dd>
        <dt>Riesgo</dt><dd>{{ estado.ultima_decision.motivo_riesgo }}</dd>
      </dl>
    </section>
    <p v-else-if="estado">Aún no hay decisiones. Inicia el bot y corre un ciclo.</p>

    <section v-if="estado?.errores.length" class="errores">
      <h2>Errores recientes</h2>
      <ul><li v-for="(e, i) in estado.errores" :key="i"><b>{{ e.etapa }}</b>: {{ e.mensaje }}</li></ul>
    </section>
  </main>
</template>

<style scoped>
main { max-width: 860px; margin: 0 auto; padding: 24px 16px; }
header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
h1 { font-size: 1.4rem; margin: 0; }
h1 small { font-weight: 400; color: #888; font-size: .9rem; }
h2 { font-size: .85rem; text-transform: uppercase; letter-spacing: .04em; color: #888; margin: 0 0 6px; }
.modo { padding: 4px 10px; border-radius: 999px; background: #444; color: #fff; font-size: .85rem; }
.modo[data-modo='activo'] { background: #1baf7a; }
.modo[data-modo='pausado'] { background: #eb6834; }
.controles { display: flex; flex-wrap: wrap; gap: 8px; margin: 20px 0; }
button { padding: 8px 14px; border-radius: 8px; border: 1px solid #2a78d6; background: transparent; color: inherit; cursor: pointer; }
button:hover:not(:disabled) { background: #2a78d6; color: #fff; }
button:disabled { opacity: .5; cursor: wait; }
.tarjetas { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
.tarjetas div, .decision, .errores { border: 1px solid #8884; border-radius: 10px; padding: 14px; }
.tarjetas p { font-size: 1.3rem; margin: 0; font-variant-numeric: tabular-nums; }
.decision, .errores { margin-top: 16px; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 6px 16px; margin: 0; }
dt { color: #888; }
dd { margin: 0; }
.error { color: #eb6834; }
</style>

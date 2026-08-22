import { useEffect, useMemo, useRef, useState } from 'react'

const ASSET_BASE = import.meta.env.VITE_VISION_ASSET_BASE || '/final-product'
const INITIAL_SUMMARY = { lot_count: 42, lot_volume_l: 161.21, confirmed_tracks: 445, detections_total: 26587, frames_processed: 749 }

function Metric({ label, value, tone = 'text-white' }) {
  return <div className="metric"><span>{label}</span><strong className={tone}>{value}</strong></div>
}

export default function App() {
  const videoRef = useRef(null)
  const warningIssued = useRef(false)
  const tripIssued = useRef(false)
  const [plcStatus, setPlcStatus] = useState('RUNNING')
  const [summary, setSummary] = useState(INITIAL_SUMMARY)
  const [progress, setProgress] = useState(0)
  const [autoGuard, setAutoGuard] = useState(true)
  const [alert, setAlert] = useState({ level: 'NORMAL', message: 'Visão operacional; relé do motor energizado.' })
  const [events, setEvents] = useState(['Modelo fine-tuned carregado', 'Homografia 5900 × 1500 mm ativa', 'Computador de segurança automático'])

  useEffect(() => {
    fetch(`${ASSET_BASE}/summary.json`).then((response) => response.ok ? response.json() : Promise.reject()).then(setSummary).catch(() => setSummary(INITIAL_SUMMARY))
  }, [])

  const liveCount = Math.min(summary.lot_count || 0, Math.floor(progress * (summary.lot_count || 0)))
  const liveVolume = ((summary.lot_volume_l || 0) * progress).toFixed(1)
  const relayClosed = plcStatus !== 'STOPPED'
  const statusTone = plcStatus === 'RUNNING' ? 'green' : plcStatus === 'WARNING' ? 'amber' : 'red'
  const confidence = useMemo(
    () => Math.round((summary.mean_mask_confidence ?? summary.mean_confidence ?? 0.39) * 100),
    [summary],
  )
  const pushEvent = (message) => setEvents((current) => [message, ...current].slice(0, 4))

  const stopTray = (reason = 'Parada manual pelo operador') => {
    videoRef.current?.pause()
    setPlcStatus('STOPPED')
    setAlert({ level: 'TRIP', message: reason })
    pushEvent(`STOP: ${reason}`)
  }
  const continueTray = () => {
    setPlcStatus('RUNNING')
    setAlert({ level: 'NORMAL', message: 'Intertravamento liberado; esteira em movimento.' })
    pushEvent('Operador liberou a esteira')
    videoRef.current?.play().catch(() => {})
  }
  const simulateRisk = () => {
    warningIssued.current = true
    setPlcStatus('WARNING')
    setAlert({ level: 'WARNING', message: 'Acúmulo/oclusão elevada: inspeção solicitada.' })
    pushEvent('WARN: oclusão e densidade acima do limite')
  }
  const resetLot = () => {
    warningIssued.current = false
    tripIssued.current = false
    setProgress(0)
    setEvents(['Novo lote iniciado'])
    setPlcStatus('RUNNING')
    setAlert({ level: 'NORMAL', message: 'Novo lote; visão operacional.' })
    if (videoRef.current) { videoRef.current.currentTime = 0; videoRef.current.play().catch(() => {}) }
  }
  const handleTimeUpdate = () => {
    const video = videoRef.current
    if (!video?.duration) return
    setProgress(video.currentTime / video.duration)
    if (!autoGuard) return
    if (video.currentTime >= 8 && !warningIssued.current) simulateRisk()
    if (video.currentTime >= 11 && !tripIssued.current) {
      tripIssued.current = true
      stopTray('Parada automática: risco persistiu 3 s sem reconhecimento')
    }
  }

  return (
    <main className="min-h-screen bg-[#070b0d] p-3 font-mono text-slate-200 lg:p-5">
      <section className="mx-auto max-w-[1500px] border border-slate-700 bg-[#0c1216] shadow-2xl">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700 px-4 py-3">
          <div><p className="text-[10px] tracking-[0.32em] text-lime-300">BATTERY VISION / HMI</p><h1 className="text-lg font-bold tracking-wider">ESTEIRA 01 · INSPEÇÃO E VOLUME</h1></div>
          <div className={`status status-${statusTone}`}><i /> PLC SIMULADO: {plcStatus}</div>
        </header>
        <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div>
            <div className="relative overflow-hidden border border-slate-600 bg-black">
              <video ref={videoRef} className="aspect-video w-full object-contain" src={`${ASSET_BASE}/final-product.mp4`} poster={`${ASSET_BASE}/preview.jpg`} controls autoPlay muted loop playsInline onTimeUpdate={handleTimeUpdate} />
              <div className="absolute left-3 top-3 border border-lime-400/60 bg-black/80 px-2 py-1 text-[10px] text-lime-300">YOLO26 SEG · KALMAN + HUNGARIAN · 960 PX</div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
              <Metric label="CRUZAMENTOS" value={String(liveCount).padStart(3, '0')} tone="text-lime-300" />
              <Metric label="VOLUME DO LOTE" value={`${liveVolume} L`} />
              <Metric label="TRACKS CONFIRMADOS" value={summary.confirmed_tracks ?? '—'} />
              <Metric label="MASK CONF." value={`~${confidence}%`} tone="text-cyan-300" />
            </div>
          </div>
          <aside className="flex flex-col gap-3">
            <div className={`decision decision-${alert.level.toLowerCase()}`}><div className="flex items-center justify-between"><span className="text-[10px] tracking-[0.2em]">COMPUTADOR DE SEGURANÇA</span><strong>{alert.level}</strong></div><p>{alert.message}</p></div>
            <div className="panel"><h2>ENTRADAS</h2><Metric label="Modelo" value="ONLINE" tone="text-lime-300" /><Metric label="Observações" value={(summary.detections_total || 0).toLocaleString('pt-BR')} /><Metric label="Bandeja" value="FULL ROI" tone="text-cyan-300" /><Metric label="Auto-guard" value={autoGuard ? 'ARMADO' : 'MANUAL'} tone={autoGuard ? 'text-lime-300' : 'text-amber-300'} /></div>
            <div className="panel"><h2>SAÍDAS SIMULADAS</h2><Metric label="Relé motor K1" value={relayClosed ? 'FECHADO' : 'ABERTO'} tone={relayClosed ? 'text-lime-300' : 'text-red-400'} /><Metric label="Sirene" value={plcStatus === 'RUNNING' ? 'OFF' : 'ON'} tone={plcStatus === 'RUNNING' ? 'text-slate-300' : 'text-amber-300'} /><Metric label="Esteira" value={plcStatus === 'STOPPED' ? 'PARADA' : 'MOVENDO'} tone={plcStatus === 'STOPPED' ? 'text-red-400' : 'text-lime-300'} /></div>
            <div className="grid grid-cols-2 gap-2"><button className="button button-warn" onClick={simulateRisk}>SIMULAR ALERTA</button><button className="button button-stop" onClick={() => stopTray()}>PARAR ESTEIRA</button><button className="button button-run" onClick={continueTray}>CONTINUAR</button><button className="button" onClick={resetLot}>RESET LOTE</button></div>
            <label className="flex cursor-pointer items-center justify-between border border-slate-700 p-2 text-[11px]">WARN → STOP automático (8–11 s)<input type="checkbox" checked={autoGuard} onChange={(event) => setAutoGuard(event.target.checked)} /></label>
            <div className="panel flex-1"><h2>EVENTOS RECENTES</h2><ol className="space-y-2 text-[10px] text-slate-400">{events.map((event, index) => <li key={`${event}-${index}`}><span className="text-slate-600">{index + 1}.</span> {event}</li>)}</ol></div>
          </aside>
        </div>
        <footer className="flex flex-wrap justify-between gap-2 border-t border-slate-700 px-4 py-2 text-[10px] text-slate-500"><span>CALIBRAÇÃO PROVISÓRIA · BANDEJA 5900 × 1500 MM · PLC SEM HARDWARE REAL</span><span>FRAME {Math.round(progress * (summary.frames_processed || 749))}/{summary.frames_processed || 749}</span></footer>
      </section>
    </main>
  )
}

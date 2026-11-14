import { useEffect, useState } from 'react'
import type { SystemState } from '../lib/types'

const fmtHour = (h: number) => `${String(Math.floor(h)).padStart(2, '0')}:${String(Math.round((h % 1) * 60)).padStart(2, '0')}`

/**
 * Vehicle telemetry. On a real mission these values come from the rover and are read-only;
 * for the demo they can be edited to change the simulation.
 */
export default function VehiclePanel({ value, onChange }: { value: SystemState; onChange: (v: SystemState) => void }) {
  const set = (key: keyof SystemState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    onChange({ ...value, [key]: Number(e.target.value) })
  const commit = (key: 'battery_capacity_kwh' | 'reserve_pct', v: number) => {
    const next = { ...value, [key]: v }
    next.battery_kwh = Math.min(next.battery_kwh, next.battery_capacity_kwh)
    onChange(next)
  }
  const pct = Math.round((value.battery_kwh / value.battery_capacity_kwh) * 100)

  return (
    <section aria-label="Vehicle telemetry" className="glass-panel w-60 rounded-2xl p-3 shadow-xl backdrop-blur-xl">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-paper">Telemetry</span>
        <span className="rounded bg-oxide/20 px-1.5 font-mono text-[8px] uppercase tracking-wider text-oxide" title="Read-only on a real mission">
          Simulation
        </span>
      </div>

      <label className="mt-2.5 block">
        <span className="flex justify-between font-mono text-[9px] uppercase tracking-[0.14em] text-faint">
          <span>Departure (local solar time)</span>
          <span className="text-paper tabular-nums">{fmtHour(value.start_hour)}</span>
        </span>
        <input type="range" min={5} max={19} step={0.25} value={value.start_hour} onChange={set('start_hour')}
          aria-label="Departure local solar time"
          className="mt-1 h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-paper/20 accent-oxide" />
      </label>

      <label className="mt-2.5 block">
        <span className="flex justify-between font-mono text-[9px] uppercase tracking-[0.14em] text-faint">
          <span>Battery</span>
          <span className="text-paper tabular-nums">{value.battery_kwh} kWh · {pct}%</span>
        </span>
        <input type="range" min={0} max={value.battery_capacity_kwh} step={1} value={value.battery_kwh} onChange={set('battery_kwh')}
          aria-label="Battery charge in kWh"
          className="mt-1 h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-paper/20 accent-oxide" />
      </label>

      <div className="mt-2.5 grid grid-cols-2 gap-2">
        <label className="block">
          <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-faint">Capacity kWh</span>
          <NumberField value={value.battery_capacity_kwh} min={5} max={200} onCommit={(v) => commit('battery_capacity_kwh', v)} />
        </label>
        <label className="block">
          <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-faint">Reserve %</span>
          <NumberField value={value.reserve_pct} min={0} max={90} onCommit={(v) => commit('reserve_pct', v)} />
        </label>
      </div>
    </section>
  )
}

/** Number input that keeps a draft while typing and only applies a valid value on blur or Enter. */
function NumberField({ value, min, max, onCommit }: { value: number; min: number; max: number; onCommit: (v: number) => void }) {
  const [draft, setDraft] = useState(String(value))
  useEffect(() => setDraft(String(value)), [value])
  const apply = () => {
    const v = Number(draft)
    if (draft.trim() === '' || !Number.isFinite(v)) return setDraft(String(value))
    const clamped = Math.min(max, Math.max(min, v))
    setDraft(String(clamped))
    if (clamped !== value) onCommit(clamped)
  }
  return (
    <input type="number" min={min} max={max} value={draft}
      onChange={(e) => setDraft(e.target.value)} onBlur={apply}
      onKeyDown={(e) => e.key === 'Enter' && (e.currentTarget as HTMLInputElement).blur()}
      className="glass-input mt-1 w-full rounded-lg px-2 py-1 font-mono text-[12px] text-paper" />
  )
}

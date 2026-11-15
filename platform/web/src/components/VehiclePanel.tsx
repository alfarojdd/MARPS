import { useEffect, useState } from 'react'
import type { SystemState } from '../lib/types'

export const fmtHour = (h: number) => `${String(Math.floor(h)).padStart(2, '0')}:${String(Math.round((h % 1) * 60)).padStart(2, '0')}`

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
    <section id="telemetry-panel" aria-label="Vehicle telemetry" className="m3-panel w-72 rounded-2xl p-4">
      <h2 className="text-base font-medium text-paper">Telemetry</h2>
      <p className="text-sm text-dim">Simulated values for the demo.</p>

      <label className="mt-3 block">
        <span className="flex items-baseline justify-between text-sm text-dim">
          <span>Departure time</span>
          <span className="font-mono tabular-nums text-paper">{fmtHour(value.start_hour)} <abbr title="Local true solar time" className="text-dim no-underline">LTST</abbr></span>
        </span>
        <input type="range" min={5} max={19} step={0.25} value={value.start_hour} onChange={set('start_hour')}
          aria-label="Departure time, local solar time" aria-valuetext={`${fmtHour(value.start_hour)} local solar time`}
          className="m3-slider mt-1" />
      </label>

      <label className="mt-3 block">
        <span className="flex items-baseline justify-between text-sm text-dim">
          <span>Battery</span>
          <span className="font-mono tabular-nums text-paper">{value.battery_kwh} kWh · {pct}%</span>
        </span>
        <input type="range" min={0} max={value.battery_capacity_kwh} step={1} value={value.battery_kwh} onChange={set('battery_kwh')}
          aria-label="Battery charge in kWh" className="m3-slider mt-1" />
      </label>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-sm text-dim">Capacity (kWh)</span>
          <NumberField value={value.battery_capacity_kwh} min={5} max={200} onCommit={(v) => commit('battery_capacity_kwh', v)} />
        </label>
        <label className="block">
          <span className="text-sm text-dim">Reserve (%)</span>
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
      className="m3-field mt-1 h-12 w-full rounded-lg px-3 font-mono text-base text-paper" />
  )
}

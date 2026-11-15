import { useState, useEffect } from 'react'
import type { MissionRequirements, Place, PlannedRoute, SystemState } from '../lib/types'
import { formatDuration, formatKm, formatLat, formatLon, siteLabel } from '../lib/format'
import { BellonaMark, MarsDot } from './Brand'

interface Props {
  prompt: string
  onPromptChange: (v: string) => void
  onPlan: () => void
  loading: boolean
  error: string | null
  requirements: MissionRequirements | null
  route: PlannedRoute | null
  places: Place[]
  focusedName: string | null
  onFocusPlace: (name: string) => void
  onResetRoute?: () => void
  onPreset?: (system: SystemState) => void
  shortcut: string
  /** One-line hint about clicking two map points for a standard MARPS route. */
  pickHint?: string
  /** 'manual': route picked on the map with default weights (no Bellona). */
  routeMode?: 'manual' | 'bellona'
}

/** Demo sorties: same origin and destination (landing site → top of the delta), so the routes differ only by mission context.
 * Each one also sets the vehicle state, so the scenario behaves as described. */
const PRESET_SORTIES: { id: string; label: string; route: string; text: string; system: SystemState }[] = [
  {
    id: '1',
    label: 'Low battery · charging stop',
    route: 'Low battery',
    text: 'Two astronauts drive from the landing site to the top of the delta. The battery is low, so save as much energy as possible and plan a sunlit stop on the way to recharge.',
    system: { start_hour: 9, battery_kwh: 16, battery_capacity_kwh: 40, reserve_pct: 20 },
  },
  {
    id: '2',
    label: 'Crew + fragile cargo',
    route: 'Fragile cargo',
    text: 'Two astronauts carrying fragile sample tubes must go from the landing site to the top of the delta. Take the safest, gentlest route possible.',
    system: { start_hour: 9, battery_kwh: 30, battery_capacity_kwh: 40, reserve_pct: 20 },
  },
  {
    id: '3',
    label: 'Science · carbonates',
    route: 'Science stops',
    text: 'From the landing site to the top of the delta. Our main goal is carbonates, plus clays if they are on the way. We have plenty of time for science stops.',
    system: { start_hour: 8, battery_kwh: 34, battery_capacity_kwh: 40, reserve_pct: 20 },
  },
]

/** Phone-sized viewport (same breakpoint as Tailwind's `sm`). Desktop layout never reads this. */
function useIsMobile() {
  const query = '(max-width: 639px)'
  const [mobile, setMobile] = useState(() => typeof window !== 'undefined' && window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const onChange = () => setMobile(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return mobile
}

export default function MissionPanel({
  prompt,
  onPromptChange,
  onPlan,
  loading,
  error,
  requirements,
  route,
  places: _places,
  onResetRoute,
  onPreset,
  shortcut,
  pickHint,
  routeMode,
}: Props) {
  // If a route exists and we are not explicitly editing, show summary mode
  const [isEditing, setIsEditing] = useState(false)
  // Phone only: Bellona hides behind a button, and the route briefing folds down to a compact bar.
  const isMobile = useIsMobile()
  const [chatOpen, setChatOpen] = useState(false)
  const [briefingFolded, setBriefingFolded] = useState(true)

  // Reset to summary view whenever a new route is received
  useEffect(() => {
    if (route) {
      setIsEditing(false)
      setBriefingFolded(true)
      setChatOpen(false)
    }
  }, [route])

  // Determine current mode: Prompt Input vs Route Summary
  const isSummaryMode = Boolean(route) && !isEditing

  const duration = route ? formatDuration(route.metrics.est_duration_min) : null

  return (
    <div className="w-full transition-all duration-300 ease-out">
      {/* =========================================================================
          STATE A: ROUTE SUMMARY & BRIEF JUSTIFICATION (Post-Plan Transformed State)
          ========================================================================= */}
      {isSummaryMode && route && duration ? (
        <div className="m3-panel pointer-events-auto mx-auto w-full max-w-4xl rounded-3xl p-4 transition-all sm:p-5">

          {/* Top Row: Route Endpoints, Status, and Edit Action */}
          <div className={`flex flex-nowrap items-center justify-between gap-2 sm:flex-wrap ${isMobile && briefingFolded ? '' : 'border-b border-outline-variant pb-3'}`}>
            <div className="flex min-w-0 flex-1 items-center gap-2 sm:flex-initial sm:flex-wrap">
              <h2 className="flex items-center gap-2 truncate text-base font-medium text-paper">
                <span className="text-paper">{siteLabel(route.originName)}</span>
                <span className="text-oxide">→</span>
                <span className="text-paper">{siteLabel(route.destinationName)}</span>
              </h2>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setIsEditing(true)
                  setChatOpen(true)
                }}
                className="btn btn-tonal"
                title="Edit the prompt or select a new sortie"
                aria-label="Edit mission"
              >
                <PencilIcon />
                <span className="hidden sm:inline">Edit mission</span>
              </button>

              {isMobile && (
                <button
                  type="button"
                  onClick={() => setBriefingFolded((f) => !f)}
                  className="btn btn-icon"
                  aria-expanded={!briefingFolded}
                  aria-label={briefingFolded ? 'Show route details' : 'Hide route details'}
                  title={briefingFolded ? 'Show route details' : 'Fold down to see the map'}
                >
                  <ChevronIcon down={!briefingFolded} />
                </button>
              )}

              {onResetRoute && (
                <button
                  type="button"
                  onClick={onResetRoute}
                  className="btn btn-icon"
                  aria-label="Clear route"
                  title="Clear route"
                >
                  <CloseIcon />
                </button>
              )}
            </div>
          </div>

          {/* Phone, folded: one line with the essentials */}
          {isMobile && briefingFolded && (
            <p className="mt-1.5 font-mono text-sm tabular-nums text-dim">
              {formatKm(route.metrics.distance_m)} km · {duration.value} {duration.unit} · {Math.round(route.metrics.battery_end_pct)} % battery
            </p>
          )}

          <div className={isMobile ? (briefingFolded ? 'hidden' : 'max-h-[55vh] overflow-y-auto overscroll-contain') : undefined}>
          {/* Middle Row: Primary Metrics Strip */}
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
            <MetricBadge
              label="Ground Dist."
              value={`${formatKm(route.metrics.distance_m)} km`}
            />
            <MetricBadge
              label="Estimated Time"
              value={`${duration.value} ${duration.unit}`}
            />
            <MetricBadge
              label="Elevation Gain"
              value={`+${route.metrics.elevation_gain_m} m`}
            />
            <MetricBadge
              label="Maximum Slope"
              value={`${route.metrics.max_slope_deg.toFixed(1)}°`}
            />
            <MetricBadge
              label="Battery on arrival"
              value={`${Math.round(route.metrics.battery_end_pct)} %`}
            />
          </div>

          {/* Bottom Row: Brief Justification & Constraints */}
          <div className="mt-3 flex flex-col gap-2 rounded-2xl border border-outline-variant bg-void/40 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0 flex-1">
              {routeMode === 'manual' ? (
                <>
                  <div className="text-sm font-medium text-oxide">MARPS · standard route</div>
                  <p className="mt-1 text-sm leading-relaxed text-paper">
                    No mission context: default weights. Describe your mission to Bellona to tailor it.
                  </p>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-2 text-sm font-medium text-oxide">
                    <MarsDot size={14} />
                    <span>Bellona · route briefing</span>
                  </div>
                  <p aria-live="polite" className="mt-1 text-sm leading-relaxed text-paper">
                    {route.explanation === null
                      ? 'Writing the briefing with the local SLM…'
                      : route.explanation || 'Briefing unavailable (SLM offline). Figures above come from the planner.'}
                  </p>
                </>
              )}
              {route.report.route?.charging_stop && (
                <p className="mt-2 text-sm text-paper">
                  <span className="text-oxide">⚡ Charging stop</span> at {route.report.route.charging_stop.arrive} for{' '}
                  {route.report.route.charging_stop.charge_hours?.toFixed(1) ?? '?'} h
                  ({formatLat(route.report.route.charging_stop.lat)} {formatLon(route.report.route.charging_stop.lon)})
                </p>
              )}
              {(route.report.route?.science_stops.length ?? 0) > 0 && (
                <p className="mt-2 text-sm text-paper">
                  <span className="text-sage">◆ Science stops</span>:{' '}
                  {route.report.route!.science_stops.map((s) => `${s.targets.join('+')} (${s.dwell_min} min)`).join(' · ')}
                </p>
              )}
              {route.warnings.map((w) => (
                <p key={w.code} className={`mt-2 text-sm ${w.severity === 'critical' ? 'text-bad' : 'text-paper'}`}>
                  ⚠ {w.message}
                </p>
              ))}
            </div>

            {/* Extracted Constraints Badges */}
            {requirements && routeMode !== 'manual' && (
              <div className="flex shrink-0 flex-wrap items-center gap-1.5 border-t border-outline-variant pt-2 sm:border-l sm:border-t-0 sm:pl-3 sm:pt-0">
                <span className="badge">
                  {requirements.human ? 'Crew EVA' : 'Rover'}
                </span>
                <span className="badge">
                  {requirements.power ? 'Solar Req' : 'Standard'}
                </span>
                <span className="badge">
                  {requirements.route_preference ?? 'Balanced'}
                </span>
              </div>
            )}
          </div>
          </div>
        </div>
      ) : isMobile && !chatOpen ? (
        /* Phone: Bellona stays out of the way behind her logo until asked */
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          aria-label="Open Bellona, the AI mission assistant"
          title="Ask Bellona"
          className="btn btn-fab pointer-events-auto relative ml-auto flex items-center justify-center !rounded-full !p-0"
          style={{ width: 56, height: 56 }}
        >
          <BellonaMark size={34} />
          {loading && <span className="absolute right-1 top-1 h-3 w-3 animate-ping rounded-full bg-oxide-bright" aria-hidden="true" />}
        </button>
      ) : (
        /* =========================================================================
           STATE B: CENTERED LOWER PROMPT BOX (Initial / Edit State from Wireframe 1)
           ========================================================================= */
        <div className="m3-panel pointer-events-auto mx-auto w-full max-w-3xl rounded-3xl p-3 transition-all">

          {/* Bellona header: MARPS is the product, Bellona is the assistant built into it */}
          <div className="mb-2 flex items-center gap-2">
            <BellonaMark size={20} />
            <span className="text-base font-semibold text-paper">Bellona</span>
            <span className="min-w-0 flex-1 truncate text-sm text-dim">AI mission assistant · built into MARPS</span>
            {isMobile && (
              <button
                type="button"
                onClick={() => {
                  setChatOpen(false)
                  setIsEditing(false)
                }}
                className="btn btn-icon shrink-0"
                aria-label="Hide Bellona"
                title="Hide Bellona"
              >
                <CloseIcon />
              </button>
            )}
          </div>

          {/* Quick examples */}
          <div className="mb-2 flex items-center gap-1.5 overflow-x-auto sm:overflow-visible" role="group" aria-label="Example missions">
            {PRESET_SORTIES.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => {
                  onPromptChange(preset.text)
                  onPreset?.(preset.system)
                }}
                className="chip shrink-0"
                aria-pressed={prompt === preset.text}
                title={preset.label}
              >
                {preset.route}
              </button>
            ))}
          </div>

          {/* Mission description + actions side by side */}
          <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
            <div className="m3-field flex-1 rounded-2xl p-1.5">
              <label htmlFor="mission-prompt" className="sr-only-text">Mission description</label>
              <textarea
                id="mission-prompt"
                rows={2}
                value={prompt}
                onChange={(e) => onPromptChange(e.target.value)}
                placeholder="Tell Bellona about your mission…"
                className="min-h-[56px] w-full resize-none bg-transparent px-2.5 py-1 text-base leading-snug text-paper placeholder:text-faint focus:outline-none"
              />
            </div>
            <div className="flex items-center justify-end gap-1 sm:flex-col sm:justify-center">
              <button
                type="button"
                onClick={onPlan}
                disabled={loading || !prompt.trim()}
                aria-busy={loading}
                aria-keyshortcuts="Control+Enter Meta+Enter"
                className="btn btn-filled"
                style={{ width: 52, padding: 0 }}
                aria-label={loading ? 'Planning…' : 'Ask Bellona'}
                title={`Ask Bellona to plan (${shortcut})`}
              >
                {loading ? <Spinner /> : <SendIcon />}
              </button>
              {route && (
                <button type="button" onClick={() => setIsEditing(false)} className="btn btn-text">
                  Cancel
                </button>
              )}
            </div>
          </div>

          {pickHint && <p className="mt-2 px-1 text-sm text-dim">{pickHint}</p>}

          {/* Error Alert */}
          {error && (
            <div role="alert" className="mt-3 rounded-xl border border-bad bg-[var(--md-error-container)] p-3 text-sm text-[var(--md-on-error-container)]">
              <strong className="font-semibold">Error: </strong>
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function MetricBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-outline-variant bg-white/[0.05] px-3 py-2">
      <div className="text-xs text-dim">{label}</div>
      <div className="mt-0.5 font-mono text-base font-semibold tabular-nums text-paper">{value}</div>
    </div>
  )
}

function SendIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  )
}

function ChevronIcon({ down }: { down: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points={down ? '6 9 12 15 18 9' : '6 15 12 9 18 15'} />
    </svg>
  )
}

function PencilIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin text-current" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

import { useState, useEffect } from 'react'
import type { MissionRequirements, Place, PlannedRoute } from '../lib/types'
import { formatDuration, formatKm, siteLabel } from '../lib/format'

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
  shortcut: string
}

const PRESET_SORTIES = [
  {
    id: '1',
    label: 'Crew · Low Exposure',
    route: 'Butler → Belva',
    text: 'Route a team from Octavia E. Butler Landing to Belva crater. Keep radiation exposure low.',
  },
  {
    id: '2',
    label: 'Rover · Fast, Solar',
    route: 'Belva → Neretva',
    text: 'Send a rover from Belva to Neretva Vallis as fast as possible, needs solar charging.',
  },
  {
    id: '3',
    label: 'EVA · Shortest Path',
    route: 'Butler → Jezero Center',
    text: 'Human EVA from Octavia E. Butler Landing to Jezero crater centre, shortest path.',
  },
]

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
  shortcut,
}: Props) {
  // If a route exists and we are not explicitly editing, show summary mode
  const [isEditing, setIsEditing] = useState(false)

  // Reset to summary view whenever a new route is received
  useEffect(() => {
    if (route) {
      setIsEditing(false)
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
        <div className="glass-panel mx-auto w-full max-w-4xl rounded-3xl p-4 shadow-2xl backdrop-blur-2xl transition-all sm:p-5">

          {/* Top Row: Route Endpoints, Status, and Edit Action */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-paper/10 pb-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="flex items-center gap-2 font-mono text-[13px] font-semibold text-paper sm:text-[14px]">
                <span className="text-paper">{siteLabel(route.originName)}</span>
                <span className="text-oxide">→</span>
                <span className="text-paper">{siteLabel(route.destinationName)}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="glass-pill flex items-center gap-1.5 rounded-xl px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.12em] text-paper transition-all hover:bg-white/[0.08] active:scale-95"
                title="Edit the prompt or select a new sortie"
              >
                <PencilIcon />
                <span>Modify Prompt</span>
              </button>

              {onResetRoute && (
                <button
                  type="button"
                  onClick={onResetRoute}
                  className="glass-pill flex h-8 w-8 items-center justify-center rounded-xl text-faint transition-all hover:bg-white/[0.08] hover:text-paper active:scale-95"
                  title="Clear route"
                >
                  <CloseIcon />
                </button>
              )}
            </div>
          </div>

          {/* Middle Row: Primary Metrics Strip */}
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-5">
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
              label="Radiation Exposure"
              value={`${route.metrics.radiation_exposure} rad·eq`}
            />
          </div>

          {/* Bottom Row: Brief Justification & Constraints */}
          <div className="mt-3 flex flex-col gap-2 rounded-2xl border border-paper/8 bg-void/40 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.2em] text-oxide">
                <span>Justification & Synthesis</span>
              </div>
              <p className="mt-1 text-[12px] italic leading-relaxed text-paper/90 sm:text-[13px]">
                "{route.explanation}"
              </p>
            </div>

            {/* Extracted Constraints Badges */}
            {requirements && (
              <div className="flex shrink-0 flex-wrap items-center gap-1.5 pt-2 sm:border-l sm:border-paper/10 sm:pl-3 sm:pt-0">
                <span className="rounded-lg border border-paper/10 bg-white/[0.04] px-2 py-1 font-mono text-[9px] uppercase tracking-wider text-dim">
                  {requirements.human ? 'Crew EVA' : 'Rover'}
                </span>
                <span className="rounded-lg border border-paper/10 bg-white/[0.04] px-2 py-1 font-mono text-[9px] uppercase tracking-wider text-dim">
                  {requirements.power ? 'Solar Req' : 'Standard'}
                </span>
                <span className="rounded-lg border border-paper/10 bg-white/[0.04] px-2 py-1 font-mono text-[9px] uppercase tracking-wider text-dim">
                  {requirements.route_preference ?? 'Balanced'}
                </span>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* =========================================================================
           STATE B: CENTERED LOWER PROMPT BOX (Initial / Edit State from Wireframe 1)
           ========================================================================= */
        <div className="glass-panel mx-auto w-full max-w-2xl rounded-3xl p-3 shadow-2xl backdrop-blur-2xl transition-all sm:p-4">

          {/* Quick Preset Chips Row */}
          <div className="mb-2.5 flex items-center gap-1.5 overflow-x-auto pb-1 text-faint">
            <span className="hidden shrink-0 font-mono text-[9px] uppercase tracking-[0.18em] text-faint sm:inline">
              Sorties:
            </span>
            {PRESET_SORTIES.map((preset) => {
              const active = prompt === preset.text
              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => onPromptChange(preset.text)}
                  className={`flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] transition-all active:scale-95 ${
                    active
                      ? 'border-oxide/60 bg-oxide/15 text-paper shadow-[0_0_12px_rgba(196,92,38,0.25)]'
                      : 'border-paper/10 bg-white/[0.03] text-dim hover:border-paper/20 hover:bg-white/[0.07] hover:text-paper'
                  }`}
                >
                  <span className="font-mono text-[9px] text-oxide">#{preset.id}</span>
                  <span>{preset.route}</span>
                </button>
              )
            })}
          </div>

          {/* Main Input Container with Circled Action Button */}
          <div className="glass-input relative flex items-center rounded-2xl p-2 transition-all">
            <textarea
              id="mission-prompt"
              rows={2}
              value={prompt}
              onChange={(e) => onPromptChange(e.target.value)}
              placeholder="e.g. Route a team from Octavia E. Butler Landing to Belva crater. Keep radiation exposure low."
              className="min-h-[48px] w-full resize-none bg-transparent px-2.5 py-1 text-[13px] leading-relaxed text-paper placeholder:text-faint/60 focus:outline-none sm:text-[14px]"
            />

            {/* Right Side: Circled Action Button (as in sketch: "Input  (b)") */}
            <div className="ml-2 flex shrink-0 items-center gap-2 pr-1">
              {route && (
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="hidden rounded-xl border border-paper/10 bg-white/[0.04] px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-dim hover:text-paper sm:inline-block"
                >
                  Cancel
                </button>
              )}

              <button
                type="button"
                onClick={onPlan}
                disabled={loading || !prompt.trim()}
                aria-label="Execute route planning"
                className="glass-circle-btn flex h-10 w-10 shrink-0 items-center justify-center disabled:cursor-not-allowed disabled:opacity-40"
                title={`Execute Route Planning (${shortcut})`}
              >
                {loading ? (
                  <Spinner />
                ) : (
                  <ArrowRightIcon />
                )}
              </button>
            </div>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mt-2.5 rounded-xl border border-bad/30 bg-bad/10 p-2.5 text-[12px] text-paper">
              <span className="font-mono text-[10px] uppercase tracking-wider text-bad">Error: </span>
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
    <div className="rounded-xl border border-paper/8 bg-void/35 p-2 text-center sm:text-left">
      <div className="font-mono text-[8px] uppercase tracking-[0.16em] text-faint">{label}</div>
      <div className="mt-0.5 font-mono text-[13px] font-semibold tracking-tight text-paper sm:text-[14px]">
        {value}
      </div>
    </div>
  )
}

function ArrowRightIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
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

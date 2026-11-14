import { useEffect, useRef, useState } from 'react'
import type { Place } from '../lib/types'
import { formatLat, formatLon } from '../lib/format'

export type BasemapMode = 'ctx' | 'hirise' | 'dtm'

interface Props {
  open: boolean
  onClose: () => void
  activeBasemap: BasemapMode
  onSelectBasemap: (m: BasemapMode) => void
  showSites: boolean
  onToggleSites: () => void
  showRoute: boolean
  onToggleRoute: () => void
  showHazards: boolean
  onToggleHazards: () => void
  showContours: boolean
  onToggleContours: () => void
  showGrid: boolean
  onToggleGrid: () => void
  overlayOpacity: number
  onChangeOverlayOpacity: (v: number) => void
  places: Place[]
  onSelectPlace: (place: Place) => void
  onResetDefaults: () => void
}

type LayersTab = 'layers' | 'places'

export default function LayersPopover({
  open,
  onClose,
  activeBasemap,
  onSelectBasemap,
  showSites,
  onToggleSites,
  showRoute,
  onToggleRoute,
  showHazards,
  onToggleHazards,
  showContours,
  onToggleContours,
  showGrid,
  onToggleGrid,
  overlayOpacity,
  onChangeOverlayOpacity,
  places,
  onSelectPlace,
  onResetDefaults,
}: Props) {
  const [tab, setTab] = useState<LayersTab>('layers')
  const popoverRef = useRef<HTMLDivElement>(null)

  // Count active layers for badge
  const activeCount =
    (activeBasemap ? 1 : 0) +
    (showSites ? 1 : 0) +
    (showRoute ? 1 : 0) +
    (showHazards ? 1 : 0) +
    (showContours ? 1 : 0) +
    (showGrid ? 1 : 0)

  // Click-outside and Escape key listener for intuitive dismissal
  useEffect(() => {
    if (!open) return

    const handlePointerDown = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onClose()
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    // Attach to document with a slight timeout so the opening click doesn't trigger it
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handlePointerDown)
      document.addEventListener('keydown', handleKeyDown)
    }, 10)

    return () => {
      clearTimeout(timer)
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      ref={popoverRef}
      role="dialog"
      aria-label="Map Layers and Data Overlays"
      className="glass-panel absolute bottom-12 left-0 z-40 w-84 max-w-[calc(100vw-2rem)] rounded-3xl p-4 shadow-2xl backdrop-blur-2xl transition-all duration-200"
    >
      {/* Popover Header */}
      <div className="flex items-center justify-between border-b border-paper/10 pb-3">
        <div className="flex items-center gap-2">
          <LayersIcon />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-paper">
            Map Layers
          </span>
          <span className="rounded-full bg-oxide/20 px-1.5 py-0.2 font-mono text-[9px] font-medium text-oxide">
            {activeCount} active
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onResetDefaults}
            className="rounded-lg px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-faint transition-all hover:bg-white/[0.06] hover:text-paper"
            title="Reset layer visibility to default"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close layers menu"
            className="grid h-6 w-6 place-items-center rounded-lg text-faint transition-all hover:bg-white/[0.08] hover:text-paper"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Segmented Sub-Tabs */}
      <div className="mt-2.5 flex rounded-xl border border-paper/10 bg-void/50 p-0.5 backdrop-blur-md">
        <button
          type="button"
          onClick={() => setTab('layers')}
          className={`flex-1 rounded-lg py-1 font-mono text-[10px] uppercase tracking-[0.14em] transition-all ${
            tab === 'layers'
              ? 'bg-paper/15 text-paper font-semibold shadow-sm'
              : 'text-dim hover:text-paper'
          }`}
        >
          Overlays & Terrain
        </button>
        <button
          type="button"
          onClick={() => setTab('places')}
          className={`flex-1 rounded-lg py-1 font-mono text-[10px] uppercase tracking-[0.14em] transition-all ${
            tab === 'places'
              ? 'bg-paper/15 text-paper font-semibold shadow-sm'
              : 'text-dim hover:text-paper'
          }`}
        >
          Sites ({places.length})
        </button>
      </div>

      {/* TAB 1: OVERLAYS & BASEMAP */}
      {tab === 'layers' && (
        <div className="mt-3 max-h-[60vh] space-y-4 overflow-y-auto pr-1">
          {/* Section 1: Basemap Imagery Selection */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-faint">
                Basemap Layer
              </span>
              <span className="font-mono text-[8px] uppercase tracking-wider text-dim">
                6 m/px Native
              </span>
            </div>

            <div className="space-y-1.5">
              <BasemapCard
                id="ctx"
                title="CTX Mosaic"
                subtitle="Calibrated 6 m/px Context Camera"
                badge="STANDARD"
                active={activeBasemap === 'ctx'}
                onSelect={() => onSelectBasemap('ctx')}
              />
              <BasemapCard
                id="hirise"
                title="HiRISE Detail"
                subtitle="High-resolution surface sharpness (0.25 m/px)"
                badge="ENHANCED"
                active={activeBasemap === 'hirise'}
                onSelect={() => onSelectBasemap('hirise')}
              />
              <BasemapCard
                id="dtm"
                title="Topographic DTM"
                subtitle="Color-shaded elevation relief & depth"
                badge="RELIEF"
                active={activeBasemap === 'dtm'}
                onSelect={() => onSelectBasemap('dtm')}
              />
            </div>
          </div>

          {/* Section 2: Science & Terrain Overlays */}
          <div className="border-t border-paper/10 pt-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-faint">
                Terrain & Science Overlays
              </span>
            </div>

            <div className="space-y-2">
              <LayerToggleRow
                label="Slope Hazards & Cliffs"
                description="Trafficability hazard zones (>15° slope)"
                active={showHazards}
                onToggle={onToggleHazards}
              />

              {showHazards && (
                <div className="ml-2 rounded-xl border border-paper/8 bg-void/40 p-2.5 transition-all">
                  <div className="flex items-center justify-between font-mono text-[9px] text-faint">
                    <span>Hazard Opacity</span>
                    <span className="text-paper">{overlayOpacity}%</span>
                  </div>
                  <input
                    type="range"
                    min={20}
                    max={100}
                    value={overlayOpacity}
                    onChange={(e) => onChangeOverlayOpacity(Number(e.target.value))}
                    className="mt-1.5 h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-paper/20 accent-oxide"
                  />
                </div>
              )}

              <LayerToggleRow
                label="Topographic Contours"
                description="10-meter elevation index contours"
                active={showContours}
                onToggle={onToggleContours}
              />

              <LayerToggleRow
                label="Lat/Lon Graticule Grid"
                description="Geodetic reference meridian grid"
                active={showGrid}
                onToggle={onToggleGrid}
              />
            </div>
          </div>

          {/* Section 3: Annotations & Waypoints */}
          <div className="border-t border-paper/10 pt-3">
            <div className="mb-2">
              <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-faint">
                Waypoints & Features
              </span>
            </div>

            <div className="space-y-2">
              <LayerToggleRow
                label="Landing Sites & POIs"
                description="Perseverance landing & crater markers"
                active={showSites}
                onToggle={onToggleSites}
              />

              <LayerToggleRow
                label="Planned Route Trajectory"
                description="Active sortie polyline & progress"
                active={showRoute}
                onToggle={onToggleRoute}
              />
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: PLACES & LANDMARKS */}
      {tab === 'places' && (
        <div className="mt-3 max-h-[60vh] space-y-1.5 overflow-y-auto pr-1">
          <p className="px-1 text-[11px] text-faint">
            Click any site to center and focus the map camera:
          </p>
          {places.map((place) => (
            <button
              key={place.name}
              type="button"
              onClick={() => {
                onSelectPlace(place)
                onClose()
              }}
              className="glass-card flex w-full items-center justify-between rounded-xl p-2.5 text-left transition-all hover:border-paper/30 active:scale-[0.98]"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-[12px] font-medium text-paper">
                  {place.name.split('(')[0].trim()}
                </div>
                <div className="mt-0.5 font-mono text-[9px] text-faint tabular-nums">
                  {formatLat(place.lat)} {formatLon(place.lon)}
                </div>
              </div>
              <span className="rounded bg-paper/10 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-dim hover:text-paper">
                Fly to →
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function BasemapCard({
  title,
  subtitle,
  badge,
  active,
  onSelect,
}: {
  id: string
  title: string
  subtitle: string
  badge: string
  active: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`glass-card flex w-full items-center justify-between rounded-xl p-2.5 text-left transition-all ${
        active
          ? 'glass-card-active'
          : 'hover:border-paper/20 hover:bg-white/[0.06]'
      }`}
    >
      <div className="min-w-0 flex-1 pr-2">
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-medium text-paper">{title}</span>
          <span
            className={`rounded px-1.5 py-0.2 font-mono text-[8px] uppercase tracking-wider ${
              active ? 'bg-oxide/20 text-oxide' : 'bg-paper/10 text-faint'
            }`}
          >
            {badge}
          </span>
        </div>
        <p className="mt-0.5 truncate text-[10px] text-faint">{subtitle}</p>
      </div>

      <div
        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-all ${
          active
            ? 'border-oxide bg-oxide text-void'
            : 'border-paper/25 bg-void/50'
        }`}
      >
        {active && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
      </div>
    </button>
  )
}

function LayerToggleRow({
  label,
  description,
  active,
  onToggle,
}: {
  label: string
  description?: string
  active: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex w-full items-center justify-between rounded-xl p-2 text-left transition-all hover:bg-white/[0.04] active:scale-[0.99]"
    >
      <div className="min-w-0 flex-1 pr-3">
        <div className="text-[12px] font-medium text-paper">{label}</div>
        {description && <div className="mt-0.5 text-[10px] text-faint">{description}</div>}
      </div>

      <div
        className={`flex h-5 w-8 shrink-0 items-center rounded-full p-0.5 transition-colors ${
          active ? 'bg-oxide' : 'bg-paper/20'
        }`}
      >
        <span
          className={`h-4 w-4 rounded-full bg-white shadow-md transition-transform ${
            active ? 'translate-x-3' : 'translate-x-0'
          }`}
        />
      </div>
    </button>
  )
}

function LayersIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-oxide">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  )
}

import { useEffect, useRef, useState } from 'react'
import type { Place, ThematicLayer } from '../lib/types'
import { formatLat, formatLon } from '../lib/format'

export type BasemapMode = 'ctx' | 'hillshade' | 'none'

interface Props {
  open: boolean
  onClose: () => void
  activeBasemap: BasemapMode
  onSelectBasemap: (m: BasemapMode) => void
  showSites: boolean
  onToggleSites: () => void
  showRoute: boolean
  onToggleRoute: () => void
  showScenes: boolean
  onToggleScenes: () => void
  sceneCount: number
  layers: ThematicLayer[]
  overlayId: string | null
  onSelectOverlay: (id: string | null) => void
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
  showScenes,
  onToggleScenes,
  sceneCount,
  layers,
  overlayId,
  onSelectOverlay,
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
    (showScenes ? 1 : 0) +
    (overlayId ? 1 : 0)
  const overlay = layers.find((l) => l.id === overlayId) ?? null
  const groups = [...new Set(layers.filter((l) => l.group !== 'Basemap').map((l) => l.group))]

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
      className="m3-panel fixed inset-x-3 top-32 z-40 max-h-[calc(100dvh-9rem)] overflow-y-auto rounded-3xl p-3 sm:absolute sm:inset-x-auto sm:bottom-14 sm:left-0 sm:top-auto sm:max-h-none sm:w-96 sm:overflow-visible sm:p-4"
    >
      {/* Popover Header */}
      <div className="flex items-center justify-between border-b border-outline-variant pb-3">
        <div className="flex items-center gap-2">
          <LayersIcon />
          <span className="text-base font-medium text-paper">
            Map layers
          </span>
          <span className="badge">
            {activeCount} active
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onResetDefaults}
            className="btn btn-text"
            title="Reset layer visibility to default"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close layers menu"
            className="btn btn-icon"
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>
      </div>

      {/* Segmented Sub-Tabs */}
      <div role="tablist" aria-label="Layers sections" className="mt-3 flex gap-2">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'layers'}
          onClick={() => setTab('layers')}
          className="chip flex-1 justify-center"
        >
          Layers & terrain
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'places'}
          onClick={() => setTab('places')}
          className="chip flex-1 justify-center"
        >
          Sites ({places.length})
        </button>
      </div>

      {/* TAB 1: OVERLAYS & BASEMAP */}
      {tab === 'layers' && (
        <div className="mt-3 max-h-[50vh] space-y-4 overflow-y-auto pr-1 sm:max-h-[60vh]">
          {/* Section 1: Basemap Imagery Selection */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium text-paper">
                Basemap
              </span>
              <span className="text-sm text-dim">
                6 m/px
              </span>
            </div>

            <div role="radiogroup" aria-label="Basemap" className="space-y-2">
              <BasemapCard
                id="ctx"
                title="CTX Mosaic"
                subtitle="Context Camera orthomosaic, 6 m/px"
                badge="IMAGE"
                active={activeBasemap === 'ctx'}
                onSelect={() => onSelectBasemap('ctx')}
              />
              <BasemapCard
                id="hillshade"
                title="Shaded relief"
                subtitle="Hillshade of the CTX elevation model, 20 m"
                badge="RELIEF"
                active={activeBasemap === 'hillshade'}
                onSelect={() => onSelectBasemap('hillshade')}
              />
            </div>
          </div>

          {/* Section 2: data layers from NASA missions */}
          <div className="border-t border-outline-variant pt-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium text-paper">
                Data layer
              </span>
              {overlayId && (
                <button
                  type="button"
                  onClick={() => onSelectOverlay(null)}
                  className="btn btn-text"
                >
                  Hide layer
                </button>
              )}
            </div>
            {layers.length === 0 && <p className="text-sm text-dim">Layers not exported yet.</p>}
            {groups.map((group) => (
              <div key={group} className="mb-2">
                <div className="mb-1 px-1 text-sm text-dim">{group}</div>
                <div className="flex flex-wrap gap-1.5">
                  {layers.filter((l) => l.group === group).map((l) => (
                    <button
                      key={l.id}
                      type="button"
                      title={`${l.subtitle}${l.coverage < 99.9 ? ` · covers ${l.coverage}% of the map` : ''}`}
                      onClick={() => onSelectOverlay(overlayId === l.id ? null : l.id)}
                      aria-pressed={overlayId === l.id}
                      className="chip"
                    >
                      {l.title}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {overlay && (
              <div className="mt-3 rounded-xl border border-outline-variant bg-white/[0.05] p-3">
                <div className="text-sm font-medium text-paper">{overlay.title}</div>
                <div className="text-sm text-dim">{overlay.subtitle}</div>
                <Legend layer={overlay} />
                <div className="mt-2 flex items-center justify-between text-sm text-dim">
                  <span>Opacity</span>
                  <span className="font-mono tabular-nums text-paper">{overlayOpacity}%</span>
                </div>
                <input
                  type="range"
                  min={20}
                  max={100}
                  value={overlayOpacity}
                  onChange={(e) => onChangeOverlayOpacity(Number(e.target.value))}
                  aria-label="Data layer opacity"
                  className="m3-slider mt-1"
                />
              </div>
            )}
          </div>

          {/* Section 3: Annotations & Waypoints */}
          <div className="border-t border-outline-variant pt-3">
            <div className="mb-2">
              <span className="text-sm font-medium text-paper">
                Waypoints & features
              </span>
            </div>

            <div className="space-y-2">
              <LayerToggleRow
                label="Landing sites & points of interest"
                description="Perseverance landing & crater markers"
                active={showSites}
                onToggle={onToggleSites}
              />

              <LayerToggleRow
                label="3D surface reconstructions"
                description={`${sceneCount} located scenes · click a 3D point to walk in`}
                active={showScenes}
                onToggle={onToggleScenes}
              />

              <LayerToggleRow
                label="Planned route"
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
        <div className="mt-3 max-h-[50vh] space-y-1.5 overflow-y-auto pr-1 sm:max-h-[60vh]">
          <p className="px-1 text-sm text-dim">
            Choose a site to centre the map on it.
          </p>
          {places.map((place) => (
            <button
              key={place.name}
              type="button"
              onClick={() => {
                onSelectPlace(place)
                onClose()
              }}
              className="m3-card flex w-full items-center justify-between rounded-xl p-2.5 text-left transition-all hover:border-outline-variant active:scale-[0.98]"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-paper">
                  {place.name.split('(')[0].trim()}
                </div>
                <div className="mt-0.5 font-mono text-xs text-dim tabular-nums">
                  {formatLat(place.lat)} {formatLon(place.lon)}
                </div>
              </div>
              <span className="badge">
                Go to
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function Legend({ layer }: { layer: ThematicLayer }) {
  const g = layer.legend
  if (g.type === 'ramp' && g.stops) {
    return (
      <div className="mt-2">
        <div className="h-2 rounded" style={{ background: `linear-gradient(90deg, ${g.stops.join(',')})` }} />
        <div className="mt-0.5 flex justify-between text-sm text-dim">
          <span>{g.vmin} {g.units}</span>
          <span>{g.vmax} {g.units}</span>
        </div>
      </div>
    )
  }
  if (g.type === 'classes' && g.items) {
    return (
      <div className="mt-3 grid grid-cols-[12px_1fr] items-center gap-x-2 gap-y-1 text-sm text-dim">
        {g.items.map((item) => (
          <FragmentRow key={`${item.value}-${item.label}`} color={item.color} label={item.label} />
        ))}
        {g.note && <p className="col-span-2 mt-1 text-sm text-dim">{g.note}</p>}
      </div>
    )
  }
  return null
}

function FragmentRow({ color, label }: { color: string; label: string }) {
  return (
    <>
      <span className="h-3 w-3 rounded-sm border border-outline" style={{ background: color }} />
      <span className="truncate">{label}</span>
    </>
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
      role="radio"
      aria-checked={active}
      onClick={onSelect}
      className={`m3-card flex min-h-14 w-full items-center justify-between rounded-xl p-3 text-left ${active ? 'm3-card-active' : ''}`}
    >
      <div className="min-w-0 flex-1 pr-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{title}</span>
          <span className="badge">{badge}</span>
        </div>
        <p className="mt-0.5 text-sm" style={{ color: 'inherit', opacity: 1 }}>{subtitle}</p>
      </div>

      <span
        aria-hidden="true"
        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
          active ? 'border-[var(--md-primary)]' : 'border-outline'
        }`}
      >
        {active && <span className="h-2.5 w-2.5 rounded-full bg-[var(--md-primary)]" />}
      </span>
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
      role="switch"
      aria-checked={active}
      onClick={onToggle}
      className="flex min-h-12 w-full items-center justify-between rounded-xl p-2 text-left hover:bg-white/[0.06]"
    >
      <span className="min-w-0 flex-1 pr-3">
        <span className="block text-sm font-medium text-paper">{label}</span>
        {description && <span className="mt-0.5 block text-sm text-dim">{description}</span>}
      </span>

      {/* M3 switch: 52x32 track, 24px thumb (28px when on, with a check) */}
      <span
        aria-hidden="true"
        className={`relative flex h-8 w-[52px] shrink-0 items-center rounded-full border-2 transition-colors ${
          active ? 'border-[var(--md-primary)] bg-[var(--md-primary)]' : 'border-outline bg-[var(--md-surface-container-highest)]'
        }`}
      >
        <span
          className={`absolute grid place-items-center rounded-full transition-all ${
            active ? 'left-[22px] h-6 w-6 bg-[var(--md-on-primary)] text-[var(--md-primary)]' : 'left-[4px] h-4 w-4 bg-outline'
          }`}
        >
          {active && <span className="text-xs leading-none">✓</span>}
        </span>
      </span>
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

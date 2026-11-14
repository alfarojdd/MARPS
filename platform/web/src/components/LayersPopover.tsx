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
          <div className="border-t border-paper/10 pt-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-faint">
                Data layer
              </span>
              {overlayId && (
                <button
                  type="button"
                  onClick={() => onSelectOverlay(null)}
                  className="rounded-lg px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-faint hover:bg-white/[0.06] hover:text-paper"
                >
                  Hide
                </button>
              )}
            </div>
            {layers.length === 0 && <p className="text-[11px] text-faint">Layers not exported yet.</p>}
            {groups.map((group) => (
              <div key={group} className="mb-2">
                <div className="mb-1 px-1 font-mono text-[8px] uppercase tracking-[0.18em] text-dim">{group}</div>
                <div className="flex flex-wrap gap-1.5">
                  {layers.filter((l) => l.group === group).map((l) => (
                    <button
                      key={l.id}
                      type="button"
                      title={`${l.subtitle}${l.coverage < 99.9 ? ` · covers ${l.coverage}% of the map` : ''}`}
                      onClick={() => onSelectOverlay(overlayId === l.id ? null : l.id)}
                      className={`rounded-full border px-2.5 py-1 text-[11px] transition-all active:scale-95 ${
                        overlayId === l.id
                          ? 'border-oxide/70 bg-oxide/20 text-paper'
                          : 'border-paper/10 bg-white/[0.03] text-dim hover:border-paper/25 hover:text-paper'
                      }`}
                    >
                      {l.title}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {overlay && (
              <div className="mt-2 rounded-xl border border-paper/8 bg-void/40 p-2.5">
                <div className="text-[11px] text-paper">{overlay.title}</div>
                <div className="text-[10px] text-faint">{overlay.subtitle}</div>
                <Legend layer={overlay} />
                <div className="mt-2 flex items-center justify-between font-mono text-[9px] text-faint">
                  <span>Opacity</span>
                  <span className="text-paper">{overlayOpacity}%</span>
                </div>
                <input
                  type="range"
                  min={20}
                  max={100}
                  value={overlayOpacity}
                  onChange={(e) => onChangeOverlayOpacity(Number(e.target.value))}
                  aria-label="Data layer opacity"
                  className="mt-1.5 h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-paper/20 accent-oxide"
                />
              </div>
            )}
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
                label="3D Surface Reconstructions"
                description={`${sceneCount} located scenes · click a 3D point to walk in`}
                active={showScenes}
                onToggle={onToggleScenes}
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

function Legend({ layer }: { layer: ThematicLayer }) {
  const g = layer.legend
  if (g.type === 'ramp' && g.stops) {
    return (
      <div className="mt-2">
        <div className="h-2 rounded" style={{ background: `linear-gradient(90deg, ${g.stops.join(',')})` }} />
        <div className="mt-0.5 flex justify-between font-mono text-[9px] text-faint">
          <span>{g.vmin} {g.units}</span>
          <span>{g.vmax} {g.units}</span>
        </div>
      </div>
    )
  }
  if (g.type === 'classes' && g.items) {
    return (
      <div className="mt-2 grid grid-cols-[10px_1fr] items-center gap-x-1.5 gap-y-0.5 text-[10px] text-dim">
        {g.items.map((item) => (
          <FragmentRow key={`${item.value}-${item.label}`} color={item.color} label={item.label} />
        ))}
        {g.note && <p className="col-span-2 mt-1 text-[9px] text-faint">{g.note}</p>}
      </div>
    )
  }
  return null
}

function FragmentRow({ color, label }: { color: string; label: string }) {
  return (
    <>
      <span className="h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
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

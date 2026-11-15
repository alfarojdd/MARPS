import { useCallback, useEffect, useRef, useState } from 'react'
import MapView from './components/MapView'
import MissionPanel from './components/MissionPanel'
import LayersPopover, { type BasemapMode } from './components/LayersPopover'
import SceneViewer from './components/SceneViewer'
import { Wordmark } from './components/Brand'
import VehiclePanel, { fmtHour } from './components/VehiclePanel'
import BellonaThinking from './components/BellonaThinking'
import { fetchTerrainSources } from './lib/terrain'
import { DEFAULT_SYSTEM, fetchPlannerPlaces, fetchReconstructions, fetchThematicLayers, parseMission, planRoute, summarizeRoute } from './lib/api'
import { buildRoute, makePlace } from './lib/plan'
import type { CtxMeta, MissionRequirements, Place, PlannedRoute, Scene, SystemState, ThematicLayer } from './lib/types'

const VERTICAL_EXAGGERATION = 3

function shortcutLabel() {
  if (typeof navigator === 'undefined') return 'Ctrl ↵'
  const platform = navigator.platform || ''
  const ua = navigator.userAgent || ''
  if (/Mac|iPhone|iPad/.test(platform) || /Mac/.test(ua)) return '⌘↵'
  return 'Ctrl ↵'
}

export default function App() {
  const [meta, setMeta] = useState<CtxMeta | null>(null)
  const [places, setPlaces] = useState<Place[]>([])
  const [prompt, setPrompt] = useState(
    'Route a team from Octavia E. Butler Landing to Belva crater. Keep radiation exposure low.',
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [requirements, setRequirements] = useState<MissionRequirements | null>(null)
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [route, setRoute] = useState<PlannedRoute | null>(null)
  const [focus, setFocus] = useState<Place | null>(null)

  // Map & Layers Controls State (Pure Frontend UI)
  const [is3D, setIs3D] = useState(false)
  const [layersOpen, setLayersOpen] = useState(false)
  const [activeBasemap, setActiveBasemap] = useState<BasemapMode>('ctx')
  const [showSites, setShowSites] = useState(true)
  const [showRoute, setShowRoute] = useState(true)
  const [showScenes, setShowScenes] = useState(true)
  const [thematic, setThematic] = useState<ThematicLayer[]>([])
  const [overlayId, setOverlayId] = useState<string | null>(null)
  const [overlayOpacity, setOverlayOpacity] = useState(70)
  const [scenes, setScenes] = useState<Scene[]>([])
  const [openScene, setOpenScene] = useState<Scene | null>(null)
  const [system, setSystem] = useState<SystemState>(DEFAULT_SYSTEM)
  const [terrainUrl, setTerrainUrl] = useState('')
  const [terrainState, setTerrainState] = useState<'idle' | 'loading' | 'ready'>('idle')
  const [replayTick, setReplayTick] = useState(0)
  const [terrainError, setTerrainError] = useState<string | null>(null)

  const handleResetLayers = useCallback(() => {
    setActiveBasemap('ctx')
    setShowSites(true)
    setShowRoute(true)
    setShowScenes(true)
    setOverlayId(null)
    setOverlayOpacity(70)
  }, [])

  useEffect(() => {
    fetchTerrainSources()
      .then((sources) => {
        // Fixed for the demo: the real CTX DTM
        setTerrainUrl((sources.find((s) => s.id === 'terrain_dtm') ?? sources[0])?.url ?? '')
      })
      .catch(() => undefined)
    fetchThematicLayers().then(setThematic).catch((err) => console.warn(err.message))
    fetchReconstructions()
      .then(({ scenes, warnings }) => {
        setScenes(scenes)
        warnings.forEach((w) => console.warn(w))
      })
      .catch((err) => console.warn('3D reconstructions unavailable:', err.message))
  }, [])

  useEffect(() => {
    Promise.all([
      fetch('/layers/ctx/meta.json').then((r) => r.json()),
      fetch('/layers/ctx/places.json').then((r) => r.json()),
    ])
      .then(async ([m, p]: [CtxMeta, Place[]]) => {
        setMeta(m)
        setPlaces(p)
        // Add the planner's own named places (delta top, carbonates...) so they show on the map too.
        try {
          const known = new Set(p.map((x) => x.name.toLowerCase().replace(/[^a-z]/g, '')))
          const extra = Object.entries(await fetchPlannerPlaces())
            .filter(([key, v]) => !p.some((x) => Math.abs(x.lon - v.lon) < 0.02 && Math.abs(x.lat - v.lat) < 0.02) && !known.has(key.replace(/[^a-z]/g, '')))
            .map(([key, v]) => makePlace(key, v.lon, v.lat, m))
          setPlaces([...p, ...extra])
        } catch {
          /* planner places are optional for drawing the map */
        }
      })
      .catch((err) => {
        console.error(err)
        setError('Failed to load map data. Make sure /layers/ctx/ is present.')
      })
  }, [])

  const plan = useCallback(async () => {
    setLoading(true)
    setError(null)
    setRoute(null)
    setRequirements(null)
    setOrigin(null)
    setDestination(null)

    try {
      const req = await parseMission(prompt)
      setRequirements(req)
      const missing = (['origin', 'destination'] as const).filter((k) => !req[k])
      if (missing.length) {
        throw new Error(`The mission text does not name the ${missing.join(' or ')}. Mention a known place.`)
      }
      if (!meta) throw new Error('Map data is not loaded yet.')

      const result = await planRoute(req, system)
      const built = buildRoute(result, meta)
      setOrigin(built.origin)
      setDestination(built.destination)
      setRoute(built.route)
      setLoading(false)

      // The briefing comes from the local SLM; the route is already on screen while it is written.
      try {
        const explanation = await summarizeRoute(result.report)
        setRoute((current) => (current?.report === result.report ? { ...current, explanation } : current))
      } catch {
        setRoute((current) =>
          current?.report === result.report ? { ...current, explanation: '' } : current,
        )
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }, [meta, prompt, system])

  // Global shortcut: Ctrl/Cmd + Enter
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault()
        if (!loading && prompt.trim()) void plan()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [loading, plan, prompt])

  const toggleFocus = useCallback((place: Place) => {
    setFocus((prev) => (prev?.name === place.name ? null : place))
  }, [])

  const handleResetRoute = useCallback(() => {
    setRoute(null)
    setRequirements(null)
    setOrigin(null)
    setDestination(null)
  }, [])

  return (
    <div className="relative h-full w-full overflow-hidden bg-void text-paper">
      {/* 1. FULL-BLEED MAP CANVAS */}
      <div className="absolute inset-0 z-0">
        <MapView
          meta={meta}
          places={places}
          route={route}
          origin={origin}
          destination={destination}
          focus={focus}
          onSelectPlace={toggleFocus}
          bottomInset={route ? 220 : 160}
          scanning={loading}
          is3D={is3D}
          showSites={showSites}
          showRoute={showRoute}
          activeBasemap={activeBasemap}
          hillshade={thematic.find((l) => l.id === 'hillshade_ctx') ?? null}
          overlay={thematic.find((l) => l.id === overlayId) ?? null}
          overlayOpacity={overlayOpacity}
          scenes={scenes}
          showScenes={showScenes}
          onOpenScene={setOpenScene}
          terrainUrl={terrainUrl}
          exaggeration={VERTICAL_EXAGGERATION}
          replayTick={replayTick}
          paused={openScene !== null}
          onTerrainState={setTerrainState}
          onTerrainError={(message) => {
            setIs3D(false)
            setTerrainState('idle')
            setTerrainError(message)
          }}
        />
      </div>

      {/* 2. TOP-LEFT: brand wordmark */}
      <div className="pointer-events-none absolute left-4 top-4 z-30">
        <h1 className="sr-only-text">MARPS Bellona: mission-aware route planner for Jezero crater, Mars</h1>
        <Wordmark />
      </div>

      {/* 3. BOTTOM-LEFT: "3D" & "LAYERS" BUTTONS (From Both Wireframes) */}
      <div className="pointer-events-auto absolute left-3 top-[4.5rem] z-40 flex flex-row flex-wrap gap-2 sm:bottom-4 sm:left-4 sm:top-auto sm:flex-col safe-bottom">
        {/* 3D / 2D Perspective Toggle Button (from Wireframe 2) */}
        <button
          type="button"
          onClick={() => {
            setTerrainError(null)
            setIs3D((prev) => !prev)
          }}
          disabled={!terrainUrl || terrainState === 'loading'}
          aria-pressed={is3D}
          className="btn btn-fab"
          title={terrainUrl ? '3D relief with the route' : '3D relief not prepared on the server'}
        >
          <CubeIcon />
          <span>{terrainState === 'loading' ? 'Loading 3D…' : is3D ? 'Back to 2D' : '3D view'}</span>
        </button>

        {is3D && route && terrainState === 'ready' && (
          <button
            type="button"
            onClick={() => setReplayTick((t) => t + 1)}
            className="btn btn-fab"
            title="Replay the route animation"
          >
            <ReplayIcon />
            <span>Replay route</span>
          </button>
        )}

        {/* Layers Button & Popover */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setLayersOpen((prev) => !prev)}
            aria-expanded={layersOpen}
            className="btn btn-fab"
            title="Map layers, science overlays and landmarks"
          >
            <LayersIcon />
            <span>Layers</span>
            {(overlayId || activeBasemap !== 'ctx') && (
              <span className="h-2 w-2 rounded-full bg-[var(--md-primary)]" aria-label="Overlay active" />
            )}
          </button>

          {/* High-Usability Frosted Glass Layers Popover */}
          <LayersPopover
            open={layersOpen}
            onClose={() => setLayersOpen(false)}
            activeBasemap={activeBasemap}
            onSelectBasemap={setActiveBasemap}
            showSites={showSites}
            onToggleSites={() => setShowSites((v) => !v)}
            showRoute={showRoute}
            onToggleRoute={() => setShowRoute((v) => !v)}
            showScenes={showScenes}
            onToggleScenes={() => setShowScenes((v) => !v)}
            sceneCount={scenes.filter((x) => x.coordinates).length}
            layers={thematic}
            overlayId={overlayId}
            onSelectOverlay={setOverlayId}
            overlayOpacity={overlayOpacity}
            onChangeOverlayOpacity={setOverlayOpacity}
            places={places}
            onSelectPlace={toggleFocus}
            onResetDefaults={handleResetLayers}
          />
        </div>
      </div>

      {/* Vehicle telemetry (editable for the demo) */}
      <VehiclePanelWrapper value={system} onChange={setSystem} />

      {terrainError && (
        <div role="alert" className="m3-panel pointer-events-auto absolute left-1/2 top-16 z-40 flex w-[90vw] max-w-md -translate-x-1/2 items-center gap-2 rounded-2xl py-2 pl-4 pr-2 text-sm text-paper sm:top-4">
          <span className="flex-1"><strong className="font-semibold text-bad">3D unavailable: </strong>{terrainError}</span>
          <button type="button" onClick={() => setTerrainError(null)} aria-label="Dismiss message" className="btn btn-icon"><span aria-hidden="true">✕</span></button>
        </div>
      )}

      <SceneViewer scene={openScene} onClose={() => setOpenScene(null)} />

      {/* Bellona thinking bubbles — appears above the mission panel during planning */}
      <BellonaThinking visible={loading} />

      {/* 4. BOTTOM-CENTER: THE CENTERED LOWER PROMPT BOX THAT TRANSFORMS INTO ROUTE SUMMARY & JUSTIFICATION */}
      <div className="pointer-events-none absolute bottom-4 left-1/2 z-30 w-full -translate-x-1/2 px-3 safe-bottom sm:bottom-4 sm:pl-[8.5rem] sm:pr-[11rem]">
        <MissionPanel
          prompt={prompt}
          onPromptChange={setPrompt}
          onPlan={() => void plan()}
          loading={loading}
          error={error}
          requirements={requirements}
          route={route}
          places={places}
          focusedName={focus?.name ?? null}
          onFocusPlace={(name) => {
            const place = places.find((p) => p.name === name)
            if (place) toggleFocus(place)
          }}
          onResetRoute={handleResetRoute}
          onPreset={setSystem}
          shortcut={shortcutLabel()}
        />
      </div>
    </div>
  )
}

/** Compact telemetry readout (time + battery). Tapping it opens the editable panel; the controls only exist for the demo. */
function VehiclePanelWrapper({ value, onChange }: { value: SystemState; onChange: (v: SystemState) => void }) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const pct = Math.round((value.battery_kwh / value.battery_capacity_kwh) * 100)
  const low = pct <= value.reserve_pct

  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={rootRef} className="pointer-events-auto absolute right-3 top-3 z-40 sm:right-4 sm:top-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls="telemetry-panel"
        aria-label={`Telemetry: departure ${fmtHour(value.start_hour)} local solar time, battery ${pct}%. ${open ? 'Close' : 'Edit'}`}
        className="btn btn-fab gap-2.5 px-3.5"
      >
        <ClockIcon />
        <span className="font-mono tabular-nums">{fmtHour(value.start_hour)}</span>
        <span aria-hidden="true" className="h-5 w-px bg-outline" />
        <BatteryIcon pct={pct} low={low} />
        <span className={`font-mono tabular-nums ${low ? 'text-bad' : ''}`}>{pct}%</span>
        <span aria-hidden="true" className={`text-xs transition-transform ${open ? 'rotate-180' : ''}`}>▾</span>
      </button>
      {open && (
        <div className="absolute right-0 top-14">
          <VehiclePanel value={value} onChange={onChange} />
        </div>
      )}
    </div>
  )
}

function ClockIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 7 12 12 15 14" />
    </svg>
  )
}

function BatteryIcon({ pct, low }: { pct: number; low: boolean }) {
  const fill = Math.max(0, Math.min(100, pct)) * 0.12
  return (
    <svg width="22" height="14" viewBox="0 0 24 14" fill="none" aria-hidden="true" className={low ? 'text-bad' : ''}>
      <rect x="1" y="1" width="19" height="12" rx="2.5" stroke="currentColor" strokeWidth="2" />
      <rect x="21.5" y="4.5" width="2" height="5" rx="1" fill="currentColor" />
      <rect x="3.5" y="3.5" width={fill} height="7" rx="1" fill="currentColor" />
    </svg>
  )
}

function LayersIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  )
}

function ReplayIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="1 4 1 10 7 10" />
      <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
    </svg>
  )
}

function CubeIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
      <line x1="12" y1="22.08" x2="12" y2="12" />
    </svg>
  )
}

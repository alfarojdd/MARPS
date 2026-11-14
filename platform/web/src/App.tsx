import { useCallback, useEffect, useState } from 'react'
import MapView from './components/MapView'
import MissionPanel from './components/MissionPanel'
import LayersPopover, { type BasemapMode } from './components/LayersPopover'
import { parseMission } from './lib/api'
import { findPlace, mockPlanRoute } from './lib/mockPlanner'
import type { CtxMeta, MissionRequirements, Place, PlannedRoute } from './lib/types'

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
  const [showHazards, setShowHazards] = useState(false)
  const [showContours, setShowContours] = useState(false)
  const [showGrid, setShowGrid] = useState(false)
  const [overlayOpacity, setOverlayOpacity] = useState(80)

  const handleResetLayers = useCallback(() => {
    setActiveBasemap('ctx')
    setShowSites(true)
    setShowRoute(true)
    setShowHazards(false)
    setShowContours(false)
    setShowGrid(false)
    setOverlayOpacity(80)
  }, [])

  useEffect(() => {
    Promise.all([
      fetch('/layers/ctx/meta.json').then((r) => r.json()),
      fetch('/layers/ctx/places.json').then((r) => r.json()),
    ])
      .then(([m, p]) => {
        setMeta(m)
        setPlaces(p)
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

      const o = findPlace(req.origin, places)
      const d = findPlace(req.destination, places)

      if (!o || !d) {
        const missing = []
        if (!o) missing.push(`origin "${req.origin}"`)
        if (!d) missing.push(`destination "${req.destination}"`)
        throw new Error(
          `Could not resolve ${missing.join(' and ')}. Demo supports: ${places.map((p) => p.name).join(', ')}`,
        )
      }

      setOrigin(o)
      setDestination(d)
      setRoute(mockPlanRoute(req, o, d))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }, [places, prompt])

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
    <div className="relative h-full w-full overflow-hidden bg-void text-paper select-none">
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
          showHazards={showHazards}
          showContours={showContours}
          showGrid={showGrid}
          overlayOpacity={overlayOpacity}
        />
      </div>

      {/* 2. TOP-LEFT: "LOGUITO" (From Both Wireframes) */}
      <div className="pointer-events-auto absolute left-4 top-4 z-30">
        <div className="glass-panel flex items-center gap-2.5 rounded-2xl px-3.5 py-2 shadow-xl backdrop-blur-xl transition-all hover:bg-white/[0.08]">
          <LoguitoMark />
          <div className="flex flex-col">
            <span className="font-mono text-[11px] font-semibold tracking-[0.24em] text-paper">
              MARPS
            </span>
            <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-dim">
              Jezero Crater
            </span>
          </div>
        </div>
      </div>

      {/* 3. BOTTOM-LEFT: "3D" & "LAYERS" BUTTONS (From Both Wireframes) */}
      <div className="pointer-events-auto absolute bottom-4 left-4 z-30 flex flex-col gap-2">
        {/* 3D / 2D Perspective Toggle Button (from Wireframe 2) */}
        <button
          type="button"
          onClick={() => setIs3D((prev) => !prev)}
          className={`glass-panel flex h-10 items-center justify-center gap-1.5 rounded-2xl px-3.5 font-mono text-[11px] uppercase tracking-[0.16em] shadow-xl backdrop-blur-xl transition-all active:scale-95 ${
            is3D
              ? 'border-oxide/70 bg-oxide/20 text-oxide shadow-[0_0_16px_rgba(196,92,38,0.3)]'
              : 'text-paper hover:bg-white/[0.08]'
          }`}
          title="Toggle 3D perspective terrain tilt"
        >
          <CubeIcon />
          <span>3D</span>
        </button>

        {/* Layers Button & Popover */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setLayersOpen((prev) => !prev)}
            aria-expanded={layersOpen}
            className={`glass-panel flex h-10 items-center justify-center gap-2 rounded-2xl px-3.5 font-mono text-[11px] uppercase tracking-[0.16em] shadow-xl backdrop-blur-xl transition-all active:scale-95 ${
              layersOpen
                ? 'border-oxide/60 bg-white/[0.14] text-paper shadow-[0_0_16px_rgba(196,92,38,0.25)]'
                : 'text-paper hover:bg-white/[0.08]'
            }`}
            title="Toggle map layers, science overlays, and landmarks"
          >
            <LayersIcon />
            <span>Layers</span>
            {(showHazards || showContours || showGrid || activeBasemap !== 'ctx') && (
              <span className="h-1.5 w-1.5 rounded-full bg-oxide" />
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
            showHazards={showHazards}
            onToggleHazards={() => setShowHazards((v) => !v)}
            showContours={showContours}
            onToggleContours={() => setShowContours((v) => !v)}
            showGrid={showGrid}
            onToggleGrid={() => setShowGrid((v) => !v)}
            overlayOpacity={overlayOpacity}
            onChangeOverlayOpacity={setOverlayOpacity}
            places={places}
            onSelectPlace={toggleFocus}
            onResetDefaults={handleResetLayers}
          />
        </div>
      </div>

      {/* 4. BOTTOM-CENTER: THE CENTERED LOWER PROMPT BOX THAT TRANSFORMS INTO ROUTE SUMMARY & JUSTIFICATION */}
      <div className="pointer-events-auto absolute bottom-4 left-1/2 z-30 w-full -translate-x-1/2 px-4 sm:bottom-6">
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
          shortcut={shortcutLabel()}
        />
      </div>
    </div>
  )
}

function LoguitoMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 16 16" aria-hidden="true" className="text-paper">
      <rect
        x="0.75"
        y="0.75"
        width="14.5"
        height="14.5"
        rx="3"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.1"
      />
      <path
        d="M3.4 12.2 L6.3 8.1 L8.3 9.5 L12.6 4.2"
        fill="none"
        stroke="#c45c26"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
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

function CubeIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
      <line x1="12" y1="22.08" x2="12" y2="12" />
    </svg>
  )
}

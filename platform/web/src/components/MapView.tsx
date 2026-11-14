import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { CtxMeta, Place, PlannedRoute, Scene, ThematicLayer } from '../lib/types'
import type { BasemapMode } from './LayersPopover'
import { formatLat, formatLon, siteLabel } from '../lib/format'
import { lonLatToPixel } from '../lib/plan'

interface Props {
  meta: CtxMeta | null
  places: Place[]
  route: PlannedRoute | null
  origin: Place | null
  destination: Place | null
  focus: Place | null
  onSelectPlace: (place: Place) => void
  bottomInset?: number
  scanning?: boolean
  is3D?: boolean
  showSites?: boolean
  showRoute?: boolean
  activeBasemap?: BasemapMode
  hillshade?: ThematicLayer | null
  overlay?: ThematicLayer | null
  overlayOpacity?: number
  scenes?: Scene[]
  showScenes?: boolean
  onOpenScene?: (scene: Scene) => void
}

export default function MapView({
  meta,
  places,
  route,
  origin,
  destination,
  focus,
  onSelectPlace,
  bottomInset = 0,
  scanning = false,
  is3D = false,
  showSites = true,
  showRoute = true,
  activeBasemap = 'ctx',
  hillshade = null,
  overlay = null,
  overlayOpacity = 80,
  scenes = [],
  showScenes = true,
  onOpenScene,
}: Props) {
  const mapRef = useRef<L.Map | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const layersRef = useRef<{
    markers?: L.LayerGroup
    route?: L.LayerGroup
    ctx?: L.LayerGroup
    base?: L.ImageOverlay
    overlay?: L.ImageOverlay
    scenes?: L.LayerGroup
  }>({})
  const openSceneRef = useRef(onOpenScene)
  openSceneRef.current = onOpenScene

  const insetsRef = useRef(bottomInset)
  insetsRef.current = bottomInset

  const selectRef = useRef(onSelectPlace)
  selectRef.current = onSelectPlace

  const [cursor, setCursor] = useState<{ lat: number; lon: number } | null>(null)
  const [mapReady, setMapReady] = useState(false)
  const [scaleInfo, setScaleInfo] = useState<{ widthPx: number; label: string }>({
    widthPx: 64,
    label: '1 km',
  })

  useEffect(() => {
    if (!containerRef.current || mapRef.current || !meta) return

    const map = L.map(containerRef.current, {
      crs: L.CRS.Simple,
      minZoom: -3,
      maxZoom: 2,
      zoomControl: true,
      attributionControl: false,
    })

    map.fitBounds([
      [-meta.rows, 0],
      [0, meta.cols],
    ])

    const tileGroup = L.layerGroup().addTo(map)
    layersRef.current.ctx = tileGroup
    meta.tiles.forEach((t) => {
      const bounds: L.LatLngBoundsExpression = [
        [-(t.row0 + t.height), t.col0],
        [-t.row0, t.col0 + t.width],
      ]
      L.imageOverlay(`/layers/ctx/${t.file}`, bounds, {
        opacity: 1,
        interactive: false,
      }).addTo(tileGroup)
    })

    layersRef.current.markers = L.layerGroup().addTo(map)
    mapRef.current = map
    setMapReady(true)

    const ro = new ResizeObserver(() => map.invalidateSize())
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      map.remove()
      mapRef.current = null
      layersRef.current = {}
      setMapReady(false)
    }
  }, [meta])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !meta) return

    const onMove = (e: L.LeafletMouseEvent) => {
      setCursor(pixelToLonLat(e.latlng.lng, -e.latlng.lat, meta))
    }
    const onOut = () => setCursor(null)
    map.on('mousemove', onMove)
    map.on('mouseout', onOut)
    return () => {
      map.off('mousemove', onMove)
      map.off('mouseout', onOut)
    }
  }, [meta])

  // Adaptive scale calculation based on zoom level and ground resolution
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady || !meta) return

    const updateScale = () => {
      // Sample 100 screen pixels horizontally
      const p1 = map.containerPointToLatLng([0, 0])
      const p2 = map.containerPointToLatLng([100, 0])
      const rasterDeltaPx = Math.abs(p2.lng - p1.lng)
      const resM = meta.resolution_m || 6
      const metersPer100Px = rasterDeltaPx * resM

      // Round distances to target: 50m, 100m, 200m, 500m, 1km, 2km, 5km, 10km, 20km, 50km
      const targetMeters = metersPer100Px
      const roundCandidates = [50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000]

      let chosenMeters = roundCandidates[0]
      for (const d of roundCandidates) {
        if (d <= targetMeters * 1.4) {
          chosenMeters = d
        }
      }

      const metersPerPx = metersPer100Px / 100
      const widthPx = Math.max(38, Math.min(130, Math.round(chosenMeters / metersPerPx)))
      const label = chosenMeters >= 1000 ? `${chosenMeters / 1000} km` : `${chosenMeters} m`

      setScaleInfo({ widthPx, label })
    }

    updateScale()
    map.on('zoom', updateScale)
    map.on('zoomend', updateScale)
    map.on('resize', updateScale)
    return () => {
      map.off('zoom', updateScale)
      map.off('zoomend', updateScale)
      map.off('resize', updateScale)
    }
  }, [mapReady, meta])

  // Update site markers
  useEffect(() => {
    const map = mapRef.current
    const markers = layersRef.current.markers
    if (!map || !markers) return

    markers.clearLayers()

    if (!showSites) return

    const named = new Set(
      [origin?.name, destination?.name].filter((name): name is string => Boolean(name)),
    )

    places.forEach((place) => {
      if (named.has(place.name)) return
      const marker = L.marker([-place.row, place.col], {
        icon: pinIcon('site', focus?.name === place.name),
        keyboard: true,
        title: place.name,
      })
      marker.bindTooltip(siteLabel(place.name), {
        direction: 'top',
        offset: [0, -8],
        className: 'marps-tip',
      })
      marker.on('click', () => selectRef.current(place))
      marker.addTo(markers)
    })

    const select = (place: Place) => selectRef.current(place)
    if (origin) addEndpoint(markers, origin, 'origin', focus?.name === origin.name, select)
    if (destination) addEndpoint(markers, destination, 'destination', focus?.name === destination.name, select)
  }, [places, origin, destination, focus, mapReady, showSites])

  // Update route polyline
  useEffect(() => {
    const map = mapRef.current
    if (!mapReady || !map) return

    if (layersRef.current.route) {
      map.removeLayer(layersRef.current.route)
      layersRef.current.route = undefined
    }

    if (!route || route.path.length < 2 || !showRoute) return

    const latlngs = route.path.map(([col, row]) => L.latLng(-row, col))
    const group = L.layerGroup().addTo(map)

    // Traditional shortest-path A* for comparison (dashed, behind the planned route)
    if (route.classicPath.length > 1) {
      L.polyline(route.classicPath.map(([col, row]) => L.latLng(-row, col)), {
        color: '#7fb4ff', weight: 2, opacity: 0.85, dashArray: '6 6', interactive: false,
      }).bindTooltip('Classic shortest path (A*)', { sticky: true }).addTo(group)
    }
    for (const stop of route.stops) {
      L.circleMarker(L.latLng(-stop.row, stop.col), {
        radius: 5, weight: 2, color: '#f4f0e6', fillOpacity: 1,
        fillColor: stop.kind === 'charging' ? '#f2c94c' : '#5fd38a',
      }).bindTooltip(stop.label).addTo(group)
    }

    // Outer shadow / glow
    L.polyline(latlngs, {
      color: '#070706',
      weight: 6,
      opacity: 0.75,
      lineCap: 'round',
      lineJoin: 'round',
      interactive: false,
    }).addTo(group)

    // High-visibility core
    L.polyline(latlngs, {
      color: '#f4f0e6',
      weight: 2,
      opacity: 1,
      lineCap: 'round',
      lineJoin: 'round',
      interactive: false,
    }).addTo(group)

    // Marching orange pulse line
    L.polyline(latlngs, {
      color: '#e26a2c',
      weight: 1.75,
      opacity: 0.95,
      dashArray: '3 14',
      lineCap: 'butt',
      className: 'route-march',
      interactive: false,
    }).addTo(group)

    layersRef.current.route = group
    const markerLayer = layersRef.current.markers
    if (markerLayer && 'bringToFront' in markerLayer) {
      ;(markerLayer as unknown as { bringToFront: () => void }).bringToFront()
    }

    const padBottom = 80 + (insetsRef.current || 0)
    map.fitBounds(L.latLngBounds(latlngs), {
      paddingTopLeft: [64, 64],
      paddingBottomRight: [64, padBottom],
    })
  }, [route, mapReady, showRoute])

  // Basemap: CTX mosaic tiles, hillshade image, or nothing
  useEffect(() => {
    const map = mapRef.current, layers = layersRef.current
    if (!mapReady || !map || !layers.ctx) return
    if (activeBasemap === 'ctx') layers.ctx.addTo(map)
    else map.removeLayer(layers.ctx)
    layers.base?.remove()
    layers.base = undefined
    if (activeBasemap === 'hillshade' && hillshade) {
      layers.base = L.imageOverlay(hillshade.url, hillshade.bounds, { interactive: false }).addTo(map)
      layers.base.bringToBack()
    }
  }, [activeBasemap, hillshade, mapReady])

  // Thematic data layer over the basemap
  useEffect(() => {
    const map = mapRef.current, layers = layersRef.current
    if (!mapReady || !map) return
    layers.overlay?.remove()
    layers.overlay = undefined
    if (!overlay) return
    layers.overlay = L.imageOverlay(overlay.url, overlay.bounds, {
      interactive: false,
      opacity: overlayOpacity / 100,
      className: overlay.kind === 'categorical' ? 'pixelated' : '',
    }).addTo(map)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [overlay, mapReady])

  useEffect(() => {
    layersRef.current.overlay?.setOpacity(overlayOpacity / 100)
  }, [overlayOpacity])

  // 3D surface reconstruction points
  useEffect(() => {
    const map = mapRef.current, layers = layersRef.current
    if (!mapReady || !map || !meta) return
    layers.scenes?.remove()
    layers.scenes = undefined
    if (!showScenes) return
    const group = L.layerGroup()
    for (const scene of scenes) {
      if (!scene.coordinates) continue
      const { col, row } = lonLatToPixel(scene.coordinates[0], scene.coordinates[1], meta)
      const local = scene.renderer !== 'sketchfab'
      const marker = L.marker([-row, col], {
        icon: L.divIcon({
          className: 'marps-pin',
          html: `<span class="scene-pin ${local ? 'scene-local' : scene.kind === 'detail' ? 'scene-detail' : ''}">3D</span>`,
          iconSize: local ? [28, 28] : [22, 22],
        }),
        title: scene.title,
        keyboard: true,
        zIndexOffset: local ? 500 : 0,
      })
      marker.bindTooltip(`${scene.title}${scene.sol ? ` · sol ${scene.sol}` : ''}`, { direction: 'top', offset: [0, -10] })
      marker.on('click', () => scene.available && openSceneRef.current?.(scene))
      marker.addTo(group)
    }
    group.addTo(map)
    layers.scenes = group
  }, [scenes, showScenes, mapReady, meta])

  // Center / Focus on selected place
  useEffect(() => {
    const map = mapRef.current
    if (!mapReady || !map || !focus) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const zoom = Math.min(map.getMaxZoom(), Math.max(map.getZoom(), 0))
    const at: L.LatLngExpression = [-focus.row, focus.col]
    if (reduce) map.setView(at, zoom)
    else map.flyTo(at, zoom, { duration: 0.65 })
  }, [focus, mapReady])

  return (
    <div className={`relative h-full w-full ${is3D ? 'map-perspective-container' : ''}`}>
      {/* MAP SURFACE WITH OPTIONAL 3D PERSPECTIVE */}
      <div
        ref={containerRef}
        className={`h-full w-full transition-all duration-700 ease-out ${
          is3D ? 'map-surface-3d' : 'map-surface-2d'
        }`}
      />

      {meta && (
        <div className="pointer-events-none absolute inset-0 z-[400]">
          {/* Reticle Corner Guides */}
          <span className="absolute left-3 top-3 h-3 w-3 border-l border-t border-paper/15" />
          <span className="absolute right-3 top-3 h-3 w-3 border-r border-t border-paper/15" />
          <span className="absolute bottom-3 left-3 h-3 w-3 border-b border-l border-paper/15" />
          <span className="absolute bottom-3 right-3 h-3 w-3 border-b border-r border-paper/15" />

          {/* BOTTOM-RIGHT "SCALE" & COORDINATES */}
          <div className="absolute right-4 bottom-4 pointer-events-auto">
            <div className="glass-panel flex flex-col items-end gap-1 rounded-2xl px-3.5 py-2 shadow-xl backdrop-blur-xl">
              {/* Graphical Scale Bar */}
              <div className="flex items-center gap-2">
                <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-dim">
                  Scale
                </span>
                <div className="flex flex-col items-center">
                  <div
                    className="flex h-1.5 items-center justify-between border-b border-l border-r border-paper/60 transition-all duration-200"
                    style={{ width: `${scaleInfo.widthPx}px` }}
                  >
                    <span className="h-1 w-px bg-paper/60" />
                    <span className="h-1 w-px bg-paper/60" />
                    <span className="h-1 w-px bg-paper/60" />
                  </div>
                  <span className="font-mono text-[8px] text-faint mt-0.5 transition-all duration-200">
                    {scaleInfo.label}
                  </span>
                </div>
              </div>

              {/* Real-time Cursor Coordinates */}
              <div className="font-mono text-[10px] tabular-nums text-paper/80">
                {cursor ? (
                  <span>
                    {formatLat(cursor.lat)} {formatLon(cursor.lon)}
                  </span>
                ) : (
                  <span className="text-faint">18.44° N 77.45° E</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Radar scanning pulse when planning */}
      {scanning && <div className="marps-scan pointer-events-none absolute inset-x-0 z-[500] h-0.5" />}

      {/* Initial satellite mosaic acquisition splash */}
      {!meta && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-void/90 backdrop-blur-xl">
          <div className="glass-panel flex flex-col items-center rounded-2xl p-6 shadow-2xl">
            <div className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-oxide opacity-75" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-oxide" />
            </div>
            <div className="mt-3 font-mono text-[10px] uppercase tracking-[0.24em] text-oxide">
              Connecting Feed
            </div>
            <div className="mt-1 text-[14px] font-medium text-paper">
              Loading Jezero CTX Orthomosaic (6 m/px)
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function addEndpoint(
  group: L.LayerGroup,
  place: Place,
  kind: 'origin' | 'destination',
  focused: boolean,
  onSelect: (place: Place) => void,
) {
  const marker = L.marker([-place.row, place.col], {
    icon: pinIcon(kind, focused),
    keyboard: true,
    title: place.name,
    zIndexOffset: 400,
  })
  marker.bindTooltip(siteLabel(place.name), {
    permanent: true,
    direction: 'right',
    offset: [12, 0],
    className: 'marps-tip',
  })
  marker.on('click', () => onSelect(place))
  marker.addTo(group)
}

function pinIcon(kind: 'site' | 'origin' | 'destination', focused: boolean) {
  const size = kind === 'site' ? 14 : 22
  const cls = [`pin-${kind}`, focused ? 'pin-focus' : ''].filter(Boolean).join(' ')
  return L.divIcon({
    className: 'marps-pin',
    html: `<span class="${cls}"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

function pixelToLonLat(col: number, row: number, meta: CtxMeta) {
  const { west, east, south, north } = meta.bounds_lonlat
  const lon = west + (col / meta.cols) * (east - west)
  const lat = north - (row / meta.rows) * (north - south)
  return { lat, lon }
}

export interface CtxTile {
  file: string
  row0: number
  col0: number
  width: number
  height: number
}

export interface CtxMeta {
  cols: number
  rows: number
  resolution_m: number
  bounds_lonlat: { west: number; east: number; south: number; north: number }
  tiles: CtxTile[]
}

/** A named site; col/row are pixels of the 6 m CTX mosaic (Leaflet CRS.Simple: lat = -row, lng = col). */
export interface Place {
  name: string
  lat: number
  lon: number
  col: number
  row: number
  tile?: string
  source?: string
}

export interface ScienceTarget {
  target: string
  priority: number
}

/** What the local LLM extracts from the mission text (POST /parse-mission). */
export interface MissionRequirements {
  human: boolean
  origin: string | null
  destination: string | null
  power: boolean
  route_preference: 'shortest' | 'fastest' | null
  safety: 'low' | 'normal' | 'high'
  science_targets: ScienceTarget[]
  science_detour: 'low' | 'medium' | 'high'
  return_to_origin: boolean
}

/** Vehicle state, set by the system and not by the LLM. */
export interface SystemState {
  start_hour: number
  battery_kwh: number
  battery_capacity_kwh: number
  reserve_pct: number
}

export interface PlanWarning {
  code: string
  severity: 'warning' | 'critical'
  message: string
}

/** Subset of the planner report used by the interface (full contract: docs/PLANNER_INTEGRATION.md). */
export interface PlanReport {
  feasible: boolean
  /** Missing when no route meets the constraints (warning NO_ROUTE) */
  route?: {
    distance_km: number
    duration_h?: number
    time_h: number
    ascent_m: number
    max_pitch_deg: number
    departure: string
    arrival: string
    battery_end_pct: number
    science_stops: { lon: number; lat: number; targets: string[]; dwell_min: number }[]
    charging_stop: { lon: number; lat: number; arrive: string; charge_hours: number } | null
  }
  comparison?: Record<string, number>
  warnings: PlanWarning[]
  [key: string]: unknown
}

export interface PlanResponse {
  report: PlanReport
  geojson: {
    features: {
      properties: { kind: string; name?: string }
      geometry: { type: string; coordinates: number[] | number[][] }
    }[]
  }
  ctx_px: { route?: [number, number][]; classic_astar?: [number, number][] }
}

export interface PlannedRoute {
  originName: string
  destinationName: string
  /** [col, row] in CTX pixels */
  path: [number, number][]
  classicPath: [number, number][]
  stops: { kind: 'science' | 'charging'; col: number; row: number; label: string }[]
  metrics: {
    distance_m: number
    est_duration_min: number
    elevation_gain_m: number
    max_slope_deg: number
    battery_end_pct: number
  }
  feasible: boolean
  warnings: PlanWarning[]
  /** One or two sentences from the local LLM; null while it is being written or if it failed. */
  explanation: string | null
  report: PlanReport
}

export interface ThematicLayer {
  id: string
  title: string
  group: string
  subtitle: string
  kind: 'image' | 'continuous' | 'categorical'
  url: string
  coverage: number
  observed: boolean
  legend: {
    type: 'image' | 'ramp' | 'classes'
    stops?: string[]
    vmin?: number
    vmax?: number
    units?: string
    items?: { value: number; color: string; label: string }[]
    note?: string
  }
  /** [[south, west], [north, east]] in the map CRS (lat = -row, lng = col) */
  bounds: [[number, number], [number, number]]
}

/** Surface reconstruction from GET /api/reconstructions (see docs/RECONSTRUCTIONS.md). */
export interface Scene {
  id: string
  title: string
  author: string
  kind: 'landscape' | 'detail' | 'aerial'
  renderer: 'spz' | 'obj' | 'sketchfab'
  coordinates: [number, number] | null
  anchor: string
  sol: number | null
  license: string
  source: string
  description?: string
  available: boolean
}

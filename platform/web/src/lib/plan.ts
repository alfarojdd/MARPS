import type { CtxMeta, Place, PlanResponse, PlannedRoute } from './types'
import { siteLabel } from './format'

/** lon/lat (planetocentric, east +) → pixels of the CTX mosaic. The projection is equirectangular, so it is linear. */
export function lonLatToPixel(lon: number, lat: number, meta: CtxMeta) {
  const { west, east, south, north } = meta.bounds_lonlat
  return {
    col: ((lon - west) / (east - west)) * meta.cols,
    row: ((north - lat) / (north - south)) * meta.rows,
  }
}

export function makePlace(name: string, lon: number, lat: number, meta: CtxMeta): Place {
  const { col, row } = lonLatToPixel(lon, lat, meta)
  return { name, lon, lat, col: Math.round(col), row: Math.round(row) }
}

/** Turns the /plan-route response into what the map and the panel draw. */
export function buildRoute(response: PlanResponse, meta: CtxMeta): { route: PlannedRoute; origin: Place | null; destination: Place | null } {
  const { report, geojson, ctx_px } = response
  if (!report.route || !ctx_px.route) {
    // No route meets the hard constraints: surface the planner's own reason.
    throw new Error(report.warnings[0]?.message ?? 'No route meets the safety constraints.')
  }
  const point = (kind: string) => geojson.features.find((f) => f.properties.kind === kind)
  const toPlace = (kind: string) => {
    const f = point(kind)
    if (!f) return null
    const [lon, lat] = f.geometry.coordinates as number[]
    return makePlace(f.properties.name ?? kind, lon, lat, meta)
  }
  const origin = toPlace('origin')
  const destination = toPlace('destination')

  const stops: PlannedRoute['stops'] = []
  for (const f of geojson.features) {
    if (f.properties.kind !== 'science_stop' && f.properties.kind !== 'charging_stop') continue
    const [lon, lat] = f.geometry.coordinates as number[]
    const { col, row } = lonLatToPixel(lon, lat, meta)
    stops.push({
      kind: f.properties.kind === 'charging_stop' ? 'charging' : 'science', col, row,
      label: f.properties.kind === 'charging_stop' ? 'Charging stop' : 'Science stop',
    })
  }

  const r = report.route
  const route: PlannedRoute = {
    originName: origin?.name ?? '',
    destinationName: destination?.name ?? '',
    path: ctx_px.route ?? [],
    classicPath: ctx_px.classic_astar ?? [],
    stops,
    metrics: {
      distance_m: r.distance_km * 1000,
      est_duration_min: (r.duration_h ?? r.time_h) * 60,
      elevation_gain_m: Math.round(r.ascent_m),
      max_slope_deg: r.max_pitch_deg,
      battery_end_pct: r.battery_end_pct,
    },
    feasible: report.feasible,
    warnings: report.warnings,
    explanation: null,
    report,
  }
  return { route, origin, destination }
}

export { siteLabel }

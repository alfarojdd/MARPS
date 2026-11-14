import type { MissionRequirements, Place, PlannedRoute, RouteMetrics } from './types'

function distancePx(a: Place, b: Place): number {
  const dx = a.col - b.col
  const dy = a.row - b.row
  return Math.sqrt(dx * dx + dy * dy)
}

function generatePath(origin: Place, dest: Place, preference: string | null): [number, number][] {
  const steps = 24
  const path: [number, number][] = []
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    // slight curve for visual interest
    const curve = Math.sin(t * Math.PI) * (preference === 'fastest' ? 40 : 80)
    const col = origin.col + (dest.col - origin.col) * t + curve * 0.3
    const row = origin.row + (dest.row - origin.row) * t - curve * 0.15
    path.push([col, row])
  }
  return path
}

export function mockPlanRoute(
  req: MissionRequirements,
  origin: Place,
  dest: Place
): PlannedRoute {
  const distPx = distancePx(origin, dest)
  const resolution_m = 6 // CTX is 6 m/px
  const distance_m = Math.round(distPx * resolution_m)

  // rough metrics influenced by mission flags
  const speed_m_per_min = req.human ? 40 : 80 // human walk vs rover
  let duration = Math.round(distance_m / speed_m_per_min)

  if (req.power) {
    // detour for solar → longer
    duration = Math.round(duration * 1.25)
  }
  if (req.route_preference === 'fastest') {
    duration = Math.round(duration * 0.85)
  }

  const elevation_gain_m = Math.round(distance_m * 0.04 + Math.random() * 30)
  const max_slope_deg = req.human ? 12 + Math.random() * 6 : 8 + Math.random() * 5

  const metrics: RouteMetrics = {
    distance_m,
    elevation_gain_m,
    max_slope_deg: Math.round(max_slope_deg * 10) / 10,
    est_duration_min: duration,
    radiation_exposure: Math.round(duration * (req.power ? 0.7 : 1.1)),
    science_points_passed: [],
  }

  const mode = req.human ? 'crew on foot' : 'rover'
  const powerNote = req.power ? ' prioritizing solar-exposed terrain' : ''
  const prefNote =
    req.route_preference === 'fastest'
      ? ' optimized for speed'
      : req.route_preference === 'shortest'
        ? ' optimized for shortest path'
        : ''

  const explanation = `Route planned for ${mode}${powerNote}${prefNote}. Distance ~${(distance_m / 1000).toFixed(1)} km with estimated ${duration} min transit. Terrain constraints and mission priorities applied.`

  return {
    path: generatePath(origin, dest, req.route_preference),
    metrics,
    explanation,
    feasible: true,
    originName: origin.name,
    destinationName: dest.name,
  }
}

/** Very simple name matcher – only known places for the demo */
export function findPlace(name: string | null, places: Place[]): Place | null {
  if (!name) return null
  const lower = name.toLowerCase().trim()

  // exact or contains
  let match = places.find((p) => p.name.toLowerCase() === lower)
  if (match) return match

  match = places.find((p) => p.name.toLowerCase().includes(lower) || lower.includes(p.name.toLowerCase().split('(')[0].trim()))
  if (match) return match

  // common aliases
  if (lower.includes('butler') || lower.includes('landing') || lower.includes('perseverance')) {
    return places.find((p) => p.name.includes('Butler')) || null
  }
  if (lower.includes('belva')) return places.find((p) => p.name.includes('Belva')) || null
  if (lower.includes('neretva')) return places.find((p) => p.name.includes('Neretva')) || null
  if (lower.includes('jezero') && !lower.includes('butler')) {
    return places.find((p) => p.name.includes('Jezero (crater')) || null
  }

  return null
}

/** Robust client-side fallback parser when backend LLM is unreachable */
export function fallbackParseMission(prompt: string): MissionRequirements {
  const lower = prompt.toLowerCase()
  const human =
    lower.includes('crew') ||
    lower.includes('human') ||
    lower.includes('eva') ||
    lower.includes('team') ||
    lower.includes('astronaut')

  const power =
    lower.includes('solar') ||
    lower.includes('charging') ||
    lower.includes('power') ||
    lower.includes('sun')

  let route_preference: 'fastest' | 'shortest' | null = null
  if (lower.includes('fast') || lower.includes('quick') || lower.includes('speed')) {
    route_preference = 'fastest'
  } else if (lower.includes('short') || lower.includes('direct')) {
    route_preference = 'shortest'
  }

  let origin = 'Octavia E. Butler Landing (Perseverance)'
  let destination = 'Belva (crater)'

  if (lower.includes('neretva') && (lower.includes('from neretva') || lower.includes('neretva to'))) {
    origin = 'Neretva Vallis'
  } else if (lower.includes('belva') && (lower.includes('from belva') || lower.includes('belva to'))) {
    origin = 'Belva (crater)'
  } else if (lower.includes('jezero') && !lower.includes('butler') && (lower.includes('from jezero') || lower.includes('jezero to'))) {
    origin = 'Jezero (crater centre)'
  } else if (lower.includes('butler') || lower.includes('landing')) {
    origin = 'Octavia E. Butler Landing (Perseverance)'
  }

  if (lower.includes('to neretva') || (origin !== 'Neretva Vallis' && lower.includes('neretva'))) {
    destination = 'Neretva Vallis'
  } else if (lower.includes('to jezero') || (origin !== 'Jezero (crater centre)' && lower.includes('jezero') && !lower.includes('butler'))) {
    destination = 'Jezero (crater centre)'
  } else if (lower.includes('to belva') || (origin !== 'Belva (crater)' && lower.includes('belva'))) {
    destination = 'Belva (crater)'
  } else if (lower.includes('to butler') || lower.includes('to landing') || (origin !== 'Octavia E. Butler Landing (Perseverance)' && (lower.includes('butler') || lower.includes('landing')))) {
    destination = 'Octavia E. Butler Landing (Perseverance)'
  }

  return { human, origin, destination, power, route_preference }
}

import type { MissionRequirements, Place } from './types'
import { formatLat, formatLon } from './format.ts'

export interface Picks {
  origin: Place | null
  destination: Place | null
}

export function pointLabel(lon: number, lat: number): string {
  return `${formatLat(lat)} ${formatLon(lon)}`
}

/** Planner point as "lon,lat" (see planner.resolve_lonlat). */
export function toPlannerPoint(place: Place): string {
  return `${place.lon.toFixed(5)},${place.lat.toFixed(5)}`
}

/** First click sets the origin, second the destination, a third starts over. */
export function nextPick(current: Picks, place: Place): Picks {
  if (!current.origin || current.destination) return { origin: place, destination: null }
  return { origin: current.origin, destination: place }
}

/** Mission with the planner's default weights, for routes picked on the map without Bellona. */
export function manualMission(origin: Place, destination: Place): MissionRequirements {
  return {
    human: true,
    origin: toPlannerPoint(origin),
    destination: toPlannerPoint(destination),
    power: false,
    route_preference: null,
    safety: 'normal',
    science_targets: [],
    science_detour: 'medium',
    return_to_origin: false,
  }
}

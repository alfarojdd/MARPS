import type { MissionRequirements, PlanResponse, Place, Scene, SystemState, ThematicLayer } from './types'

const BASE = '/api'

async function request<T>(path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new Error('Cannot reach the MARPS server. Is backend/run.sh running?')
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((d: { loc?: string[]; msg: string }) => `${d.loc?.at(-1)}: ${d.msg}`).join('; ')
      : data.detail
    throw new Error(detail || `Server error ${response.status}`)
  }
  return data as T
}

export const DEFAULT_SYSTEM: SystemState = {
  start_hour: 9,
  battery_kwh: 30,
  battery_capacity_kwh: 40,
  reserve_pct: 20,
}

export const parseMission = (prompt: string) => request<MissionRequirements>('/parse-mission', { prompt })

export const planRoute = (mission: MissionRequirements, system: SystemState = DEFAULT_SYSTEM) =>
  request<PlanResponse>('/plan-route', { mission, system })

export async function summarizeRoute(report: PlanResponse['report']): Promise<string> {
  return (await request<{ summary: string }>('/summarize-route', { report })).summary
}

export async function fetchPlannerPlaces(): Promise<Record<string, { lon: number; lat: number }>> {
  return (await request<{ places: Record<string, { lon: number; lat: number }> }>('/places')).places
}

export type { Place }

export async function fetchReconstructions(): Promise<{ scenes: Scene[]; warnings: string[] }> {
  return request<{ scenes: Scene[]; warnings: string[] }>('/reconstructions')
}

export async function fetchThematicLayers(): Promise<ThematicLayer[]> {
  const response = await fetch('/layers/thematic/layers.json')
  if (!response.ok) throw new Error('Thematic layers not exported (data/jezero/pipeline/export_web_layers.py)')
  return response.json()
}

/** URL of the scene viewer: Sketchfab embed, or the local SPZ/OBJ viewer served by the MARPS server. */
export function sceneViewerUrl(scene: Scene): string {
  if (scene.renderer === 'sketchfab') {
    const nav = scene.kind === 'landscape' ? 'fps' : 'orbit'
    return `https://sketchfab.com/models/${encodeURIComponent(scene.id)}/embed?autostart=1&preload=1&navigation=${nav}`
  }
  return `/viewer/surface.html?id=${encodeURIComponent(scene.id)}`
}

import type { CtxMeta, Scene } from './types'
import { lonLatToPixel } from './plan'

/** Subset of the Three.js terrain viewer in platform/viewer/terrain3d/terrain3d.mjs that the app uses. */
export interface Terrain3DLike {
  active: boolean
  load(url: string): Promise<{ fit?: { corr: number; rmse_m: number } } | null>
  setRoute(input: unknown): void
  enter(view: TerrainView): Promise<void>
  exit(): Promise<TerrainView | null>
  replayRoute(): Promise<void>
  setExaggeration(v: number): void
  setTextureLayers(o: { baseUrl?: string | null; overlayUrl?: string | null; opacity?: number; pixelated?: boolean }): Promise<void>
  setPaused(p: boolean): void
  focusAtXY(x: number, y: number, visibleHeight?: number): void
  projectPoint(lonLat: [number, number]): { x: number; y: number } | null
  on(fn: (type: string, data?: unknown) => void): () => void
  dispose(): void
}

export interface TerrainView {
  x: number
  y: number
  height: number
}

export interface TerrainSource {
  id: string
  title: string
  url: string
}

type Terrain3DModule = { Terrain3D: new (container: HTMLElement, options?: object) => Terrain3DLike }

const MODULE_URL = '/viewer/terrain3d/terrain3d.mjs'
const R = 3396190
const DEG = Math.PI / 180

/** Loads the Three.js viewer served by the MARPS server (needs the importmap in index.html). */
export async function loadTerrainModule(): Promise<Terrain3DModule> {
  return import(/* @vite-ignore */ MODULE_URL)
}

export async function fetchTerrainSources(): Promise<TerrainSource[]> {
  const response = await fetch('/api/terrain-sources')
  if (!response.ok) return []
  return (await response.json()).sources ?? []
}

export const lonLatToXY = (lon: number, lat: number): [number, number] => [R * lon * DEG, R * lat * DEG]
export const xyToLonLat = (x: number, y: number): [number, number] => [x / (R * DEG), y / (R * DEG)]

export function pixelToLonLat(col: number, row: number, meta: CtxMeta): [number, number] {
  const { west, east, south, north } = meta.bounds_lonlat
  return [west + (col / meta.cols) * (east - west), north - (row / meta.rows) * (north - south)]
}

/** Framing of the 2D map (CRS.Simple pixels, lat = -row) as centre and visible height in Mars metres. */
export function viewFromMap(
  center: { lat: number; lng: number },
  visibleRows: number,
  meta: CtxMeta,
): TerrainView {
  const [lon, lat] = pixelToLonLat(center.lng, -center.lat, meta)
  const [x, y] = lonLatToXY(lon, lat)
  return { x, y, height: visibleRows * meta.resolution_m }
}

/** Inverse of viewFromMap: where the 2D map should be centred and at which zoom after leaving 3D. */
export function mapFromView(view: TerrainView, meta: CtxMeta, containerHeight: number) {
  const [lon, lat] = xyToLonLat(view.x, view.y)
  const { col, row } = lonLatToPixel(lon, lat, meta)
  const rows = view.height / meta.resolution_m
  return { center: [-row, col] as [number, number], zoom: Math.log2(containerHeight / rows) }
}

export function scenePinPosition(t3d: Terrain3DLike, scene: Scene) {
  return scene.coordinates ? t3d.projectPoint(scene.coordinates) : null
}

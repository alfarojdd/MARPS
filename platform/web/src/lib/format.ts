const SHORT_LABELS: Record<string, string> = {
  'octavia e. butler landing': 'Butler',
  'jezero (crater centre)': 'Jezero centre',
  'belva (crater)': 'Belva',
  'neretva vallis': 'Neretva',
}

/** Compact display name for a site; accepts display names ("Belva (crater)") and planner keys ("delta_top"). */
export function siteLabel(name: string): string {
  const key = name.toLowerCase().replace(/\s*\(perseverance\)/, '')
  if (SHORT_LABELS[key]) return SHORT_LABELS[key]
  const plain = name.replace(/\s*\(.*\)\s*$/, '').replace(/_/g, ' ')
  return plain.charAt(0).toUpperCase() + plain.slice(1)
}

export function formatKm(meters: number): string {
  return (meters / 1000).toFixed(meters >= 10000 ? 1 : 2)
}

export function formatDuration(minutes: number): { value: string; unit: string } {
  if (minutes >= 90) return { value: (minutes / 60).toFixed(1), unit: 'h' }
  return { value: String(Math.round(minutes)), unit: 'min' }
}

export function formatLat(lat: number): string {
  return `${Math.abs(lat).toFixed(4)}°${lat >= 0 ? 'N' : 'S'}`
}

export function formatLon(lon: number): string {
  return `${Math.abs(lon).toFixed(4)}°${lon >= 0 ? 'E' : 'W'}`
}

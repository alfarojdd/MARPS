// WCAG 2.2 AA + Material 3 checks for the colour tokens and source styles. Run: npm run check:a11y
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const css = readFileSync('src/index.css', 'utf8')
const tok = Object.fromEntries([...css.matchAll(/--md-([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)].map((m) => [m[1], m[2]]))

const lum = (hex) => {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
}
const ratio = (a, b) => {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}
// Worst contrast of a two-tone mark (fill + casing) over ANY background colour.
const worstOverAnyBackground = (fill, casing) => {
  let worst = Infinity
  for (let y = 0; y <= 1; y += 0.002) {
    const r = (a) => (Math.max(a, y) + 0.05) / (Math.min(a, y) + 0.05)
    worst = Math.min(worst, Math.max(r(lum(fill)), r(lum(casing))))
  }
  return worst
}

const results = []
const need = (name, value, min) => results.push({ name, value, min, ok: value >= min })
// ── Frosted glass: blend translucent colours over the worst backdrop (white) and over black
const parseRgba = (v) => { const m = v.match(/rgba?\(([^)]+)\)/); const p = m[1].split(',').map((x) => parseFloat(x)); return { rgb: p.slice(0, 3), a: p[3] ?? 1 } }
const toHex = (c) => '#' + c.map((x) => Math.round(x).toString(16).padStart(2, '0')).join('')
const over = (top, bottom) => toHex(top.rgb.map((c, i) => c * top.a + bottom[i] * (1 - top.a)))
const hexRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16))
const glassVar = (n) => parseRgba(css.match(new RegExp(`--md-${n}:\\s*(rgba?\\([^)]*\\))`))[1])
const WHITE = [255, 255, 255]
const glass = over(glassVar('glass'), WHITE)
const glassHigh = over(glassVar('glass-high'), WHITE)
const glassCard = over({ rgb: [255, 255, 255], a: 0.09 }, hexRgb(glass)) // card on hover
const glassField = over({ rgb: [0, 0, 0], a: 0.3 }, hexRgb(glass))
const glassSurfaces = { 'glass panel (over white)': glass, 'glass button/tooltip (over white)': glassHigh, 'card inside glass (hover)': glassCard, 'field inside glass': glassField }
const t = (n) => tok[n] ?? (() => { throw new Error(`missing token --md-${n}`) })()

const surfaces = ['surface', 'surface-container', 'surface-container-high', 'surface-container-highest']
for (const s of surfaces) {
  for (const fg of ['on-surface', 'on-surface-variant', 'primary', 'tertiary', 'error']) {
    need(`text ${fg} on ${s}`, ratio(t(fg), t(s)), 4.5)
  }
}
for (const [sn, sc] of Object.entries(glassSurfaces)) {
  for (const fg of ['on-surface', 'on-surface-variant', 'primary', 'tertiary', 'error']) need(`text ${fg} on ${sn}`, ratio(t(fg), sc), 4.5)
  need(`UI outline on ${sn}`, ratio(t('outline'), sc), 3)
}
need('on-primary on primary (filled button)', ratio(t('on-primary'), t('primary')), 4.5)
need('on-primary on primary hover (#ffc9aa)', ratio(t('on-primary'), '#ffc9aa'), 4.5)
need('on-primary-container on primary-container', ratio(t('on-primary-container'), t('primary-container')), 4.5)
need('on-secondary-container on secondary-container', ratio(t('on-secondary-container'), t('secondary-container')), 4.5)
need('on-secondary-container on tonal hover (#5d4d44)', ratio(t('on-secondary-container'), '#5d4d44'), 4.5)
need('on-error-container on error-container', ratio(t('on-error-container'), t('error-container')), 4.5)
need('on-surface-variant on secondary-container (chips)', ratio(t('on-surface-variant'), t('secondary-container')), 4.5)
need('on-surface-variant on primary-container (active card subtitle)', ratio(t('on-surface-variant'), t('primary-container')), 4.5)
need('primary on secondary-container (preset number)', ratio(t('primary'), t('secondary-container')), 4.5)
need('on-surface on primary-container', ratio(t('on-surface'), t('primary-container')), 4.5)
for (const s of surfaces) need(`UI outline on ${s} (borders, icons)`, ratio(t('outline'), t(s)), 3)
for (const s of surfaces) need(`focus ring (primary) on ${s}`, ratio(t('primary'), t(s)), 3)
need('primary-container vs surface-container (selected state)', ratio(t('primary-container'), t('surface-container')) , 1.0)
need('primary border on primary-container', ratio(t('primary'), t('primary-container')), 3)

// Marks drawn straight on the map layers
const halo = t('map-halo')
for (const [name, fill] of [['site pin / route core', t('map-light')], ['destination pin', t('primary')], ['3D scene pin', '#5fc9c0'],
  ['local scene pin', '#ff9a5c'], ['detail scene pin', '#c9b8ff'], ['classic path', '#9cc7ff'], ['charging stop', '#f2c94c'], ['science stop', '#5fd38a']]) {
  need(`map mark "${name}" over any layer`, worstOverAnyBackground(fill, halo), 3)
}
need('scene pin number (#070706) on teal', ratio('#070706', '#5fc9c0'), 4.5)
need('scene pin number on local', ratio('#070706', '#ff9a5c'), 4.5)
need('scene pin number on detail', ratio('#070706', '#c9b8ff'), 4.5)

// Source rules: M3 type scale (nothing under 12px), no translucent text, no tiny hit targets
const files = []
const walk = (d) => readdirSync(d).forEach((f) => { const p = join(d, f); statSync(p).isDirectory() ? walk(p) : /\.(tsx?|css)$/.test(f) && files.push(p) })
walk('src')
const problems = []
for (const f of files) {
  const src = readFileSync(f, 'utf8')
  src.split('\n').forEach((line, i) => {
    for (const m of line.matchAll(/text-\[(\d+(?:\.\d+)?)px\]/g)) if (+m[1] < 12) problems.push(`${f}:${i + 1} text-[${m[1]}px] is under 12px`)
    for (const m of line.matchAll(/font-size:\s*(\d+(?:\.\d+)?)px/g)) if (+m[1] < 12) problems.push(`${f}:${i + 1} font-size ${m[1]}px is under 12px`)
    for (const m of line.matchAll(/font:\s*\d+\s+(\d+(?:\.\d+)?)px/g)) if (+m[1] < 12) problems.push(`${f}:${i + 1} font ${m[1]}px is under 12px`)
    if (/\b(?:sm:)?text-(?:paper|dim|faint|oxide|sage|bad)\/\d+/.test(line)) problems.push(`${f}:${i + 1} translucent text colour (contrast depends on background)`)
    if (/\buppercase\b/.test(line) && f.endsWith('.tsx')) problems.push(`${f}:${i + 1} uppercase text (M3 uses sentence case)`)
    if (/\bglass-(?:panel|pill|card|input|btn|circle|tab)/.test(line)) problems.push(`${f}:${i + 1} translucent glass class`)
  })
}

let failed = 0
for (const r of results) {
  if (!r.ok) failed++
  console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.value.toFixed(2).padStart(5)} ≥ ${r.min}  ${r.name}`)
}
problems.forEach((p) => console.log(`FAIL  ${p}`))
failed += problems.length
console.log(`\n${results.length + 0} contrast checks, ${problems.length} source problems → ${failed ? 'FAILED' : 'OK'}`)
process.exit(failed ? 1 : 0)

import { useState } from 'react'

/** Mars ball used as the "o" of Bellona and as the assistant avatar. */
export function MarsDot({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="16" cy="16" r="15" fill="#d24b1a" stroke="#fff" strokeWidth="1.5" />
      <ellipse cx="16" cy="8.5" rx="5" ry="2.2" fill="#f4d9cc" opacity=".9" />
      <path d="M4.5 18c3-2.4 5.6.4 8.6-.6s5-3 8.4-1.2 4.6 1.4 6-.4" fill="none" stroke="#7b2a10" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

/**
 * "MARPS" wordmark for the map corner. MARPS is the product (map + planner); Bellona, the AI assistant,
 * is named in the mission panel. Uses public/brand/marps-dark.svg and falls back to the same lettering as text.
 */
export function Wordmark() {
  const [image, setImage] = useState(true)
  return (
    <div className="m3-panel flex items-center rounded-2xl px-3 py-1.5" aria-label="MARPS">
      {image ? (
        <img src="/brand/marps-dark.svg" alt="MARPS" className="h-8 w-auto" onError={() => setImage(false)} />
      ) : (
        <span className="brand-wordmark text-2xl font-extrabold leading-none tracking-wide text-[#e8683a]">MARPS</span>
      )}
    </div>
  )
}

/** Bellona's Mars "o" from the logo (public/brand/bellona-o.svg), used as the assistant mark. */
export function BellonaMark({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10.2" fill="#C1440E" />
      <ellipse cx="12" cy="6.2" rx="4.2" ry="1.4" fill="#F6E7D6" />
      <path d="M5,13 C8,11.5 10,14 12.5,12.6 S17,11.6 19,13" fill="none" stroke="#7A2A0C" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

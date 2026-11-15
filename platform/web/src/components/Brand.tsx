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
 * "MARPS Bellona" wordmark for the map corner (Google Maps style). Uses public/brand/marps-bellona.png when
 * it exists and falls back to the same lettering drawn in the page.
 */
export function Wordmark() {
  const [image, setImage] = useState(true)
  return (
    <div className="m3-panel flex items-center rounded-2xl px-3 py-1.5" aria-label="MARPS Bellona">
      {image ? (
        <img src="/brand/marps-bellona-dark.svg" alt="MARPS Bellona" className="h-8 w-auto" onError={() => setImage(false)} />
      ) : (
        <span className="brand-wordmark flex items-baseline gap-2 text-sm leading-none">
          <span className="font-extrabold tracking-wide text-[#bf3f14]">MARPS</span>
          <span className="flex items-center font-semibold text-[#4a4644]">
            Bell
            <span className="mx-[1px] inline-flex translate-y-[2px]">
              <MarsDot size={15} />
            </span>
            na
          </span>
        </span>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'

const MESSAGES = [
  'Bellona is calculating…',
  'Scanning the terrain…',
  'Let Bellona guide you…',
  'Analysing radiation data…',
  'Plotting the safest path…',
  'Bellona is on it…',
  'Mapping hazard zones…',
  'Computing energy budget…',
  'Routing through Jezero…',
  'Bellona is thinking…',
]

const MESSAGE_INTERVAL = 2200   // ms per phrase
const FADE_DURATION    = 400    // ms — must match CSS

export default function BellonaThinking({ visible }: { visible: boolean }) {
  const [msgIndex, setMsgIndex] = useState(0)
  const [fadeIn,   setFadeIn]   = useState(true)

  /* Cycle through phrases with a cross-fade */
  useEffect(() => {
    if (!visible) return
    setMsgIndex(0)
    setFadeIn(true)

    const interval = setInterval(() => {
      // fade out
      setFadeIn(false)
      setTimeout(() => {
        setMsgIndex((i) => (i + 1) % MESSAGES.length)
        setFadeIn(true)
      }, FADE_DURATION)
    }, MESSAGE_INTERVAL)

    return () => clearInterval(interval)
  }, [visible])

  if (!visible) return null

  return (
    <div
      aria-live="polite"
      aria-label="Bellona AI is working"
      className="pointer-events-none absolute bottom-[200px] left-1/2 z-20 -translate-x-1/2 sm:bottom-[220px]"
    >
      {/* Speech bubble container */}
      <div className="bellona-bubble relative flex flex-col items-center gap-3">

        {/* ── Animated dot cluster ── */}
        <div className="flex items-end gap-[5px]">
          <Bubble delay={0}   size={9}  />
          <Bubble delay={120} size={12} />
          <Bubble delay={240} size={9}  />
        </div>

        {/* ── Frosted glass pill with rotating text ── */}
        <div
          className="glass-panel flex items-center gap-2.5 rounded-full px-4 py-2 shadow-2xl"
          style={{ backdropFilter: 'blur(20px) saturate(200%)' }}
        >
          {/* Pulsing mars dot */}
          <span className="bellona-dot-pulse relative flex h-2 w-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-oxide opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-oxide" />
          </span>

          {/* Rotating message */}
          <span
            className="bellona-msg font-mono text-[11px] uppercase tracking-[0.18em] text-paper/90"
            style={{
              opacity:    fadeIn ? 1 : 0,
              transform:  fadeIn ? 'translateY(0)' : 'translateY(4px)',
              transition: `opacity ${FADE_DURATION}ms ease, transform ${FADE_DURATION}ms ease`,
              whiteSpace: 'nowrap',
            }}
          >
            {MESSAGES[msgIndex]}
          </span>
        </div>
      </div>
    </div>
  )
}

/* ── Single animated bubble dot ── */
function Bubble({ delay, size }: { delay: number; size: number }) {
  return (
    <span
      className="bellona-bubble-dot rounded-full bg-oxide/70"
      style={{
        width:  size,
        height: size,
        animationDelay: `${delay}ms`,
      }}
    />
  )
}

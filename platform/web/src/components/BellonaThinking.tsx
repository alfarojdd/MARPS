import { useEffect, useState } from 'react'

const MESSAGES = [
  'Bellona is calculating…',
  'Scanning the terrain…',
  'Let Bellona guide you…',
  'Analyzing radiation data…',
  'Plotting the safest path…',
  'Bellona is on it…',
  'Mapping hazard zones…',
  'Computing energy budget…',
  'Routing through Jezero…',
  'Bellona is optimizing…',
]

const MESSAGE_INTERVAL = 1400 // faster rotation
const FADE_DURATION = 250 // crisp fade

export default function BellonaThinking({ visible }: { visible: boolean }) {
  const [msgIndex, setMsgIndex] = useState(0)
  const [fadeIn, setFadeIn] = useState(true)

  /* Cycle through phrases with a clean cross-fade */
  useEffect(() => {
    if (!visible) return
    setMsgIndex(0)
    setFadeIn(true)

    const interval = setInterval(() => {
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
      className="pointer-events-none absolute bottom-[185px] left-1/2 z-30 -translate-x-1/2 px-4 safe-bottom sm:bottom-[195px]"
    >
      {/* Speech bubble container directly in user's target zone */}
      <div className="bellona-bubble relative flex flex-col items-center gap-2.5">
        {/* Animated fast bouncing bubbles / thought circles */}
        <div className="flex items-center gap-1.5">
          <Bubble delay={0} size={8} />
          <Bubble delay={100} size={11} />
          <Bubble delay={200} size={15} />
          <Bubble delay={300} size={11} />
          <Bubble delay={400} size={8} />
        </div>

        {/* Frosted glass badge with rotating guidance text */}
        <div
          className="glass-panel flex items-center gap-2.5 rounded-full border border-oxide/40 bg-void/80 px-4 py-1.5 shadow-[0_8px_30px_rgba(0,0,0,0.7),0_0_20px_rgba(196,92,38,0.25)] backdrop-blur-xl"
        >
          {/* Animated beacon dot */}
          <span className="relative flex h-2.5 w-2.5 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-oxide-bright opacity-85" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-oxide" />
          </span>

          {/* Clean rotating prompt text */}
          <span
            className="font-mono text-[11px] font-medium tracking-[0.14em] text-paper sm:text-[12px]"
            style={{
              opacity: fadeIn ? 1 : 0,
              transform: fadeIn ? 'translateY(0) scale(1)' : 'translateY(3px) scale(0.98)',
              transition: `opacity ${FADE_DURATION}ms cubic-bezier(0.16, 1, 0.3, 1), transform ${FADE_DURATION}ms cubic-bezier(0.16, 1, 0.3, 1)`,
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

function Bubble({ delay, size }: { delay: number; size: number }) {
  return (
    <span
      className="bellona-bubble-dot rounded-full bg-gradient-to-t from-oxide to-oxide-bright shadow-[0_0_10px_rgba(196,92,38,0.6)]"
      style={{
        width: size,
        height: size,
        animationDelay: `${delay}ms`,
      }}
    />
  )
}


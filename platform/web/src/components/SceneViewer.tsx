import { useEffect, useRef } from 'react'
import type { Scene } from '../lib/types'
import { sceneViewerUrl } from '../lib/api'

const KIND_LABEL = { landscape: 'Scene', detail: 'Rock detail', aerial: 'Aerial view' } as const

/** Full-screen modal with a surface reconstruction (local SPZ/OBJ viewer or Sketchfab embed). */
export default function SceneViewer({ scene, onClose }: { scene: Scene | null; onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (scene && !dialog.open) dialog.showModal()
    if (!scene && dialog.open) dialog.close()
  }, [scene])

  // The local viewer asks to close with postMessage when Esc is pressed inside its iframe.
  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.origin === location.origin && event.data === 'marps:close-surface') onClose()
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [onClose])

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-label={scene ? `3D reconstruction: ${scene.title}` : undefined}
      className="scene-dialog glass-panel m-auto h-[88vh] w-[min(1200px,94vw)] max-w-none rounded-3xl p-0 text-paper backdrop:bg-void/70 backdrop:backdrop-blur-sm"
    >
      {scene && (
        <div className="flex h-full flex-col">
          <header className="flex items-start justify-between gap-3 border-b border-paper/10 px-4 py-3">
            <div className="min-w-0">
              <div className="truncate text-[14px] font-semibold">{scene.title}</div>
              <div className="truncate text-[11px] text-faint">
                {scene.author} · {KIND_LABEL[scene.kind]}
                {scene.sol ? ` · sol ${scene.sol}` : ''} · {scene.license}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              autoFocus
              className="glass-pill shrink-0 rounded-xl px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.12em] hover:bg-white/[0.08]"
            >
              Back to map ✕
            </button>
          </header>
          <iframe
            key={scene.id}
            title={`3D reconstruction: ${scene.title}`}
            src={sceneViewerUrl(scene)}
            allow="autoplay; fullscreen; xr-spatial-tracking"
            allowFullScreen
            className="min-h-0 flex-1 bg-black"
          />
          <footer className="flex items-center justify-between gap-3 px-4 py-2 text-[11px] text-faint">
            <span className="truncate">
              {scene.renderer === 'sketchfab'
                ? `${scene.anchor} · External viewer: use Sketchfab's first-person mode.`
                : 'Drag to look around, WASD / arrows to walk.'}
            </span>
            <a href={scene.source} target="_blank" rel="noopener noreferrer" className="shrink-0 text-dim hover:text-paper">
              Original source ↗
            </a>
          </footer>
        </div>
      )}
    </dialog>
  )
}

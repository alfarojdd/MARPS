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
      className="scene-dialog m3-panel m-auto h-[88vh] w-[min(1200px,96vw)] max-w-none rounded-3xl p-0 text-paper  sm:h-[88vh] sm:w-[min(1200px,94vw)]"
    >
      {scene && (
        <div className="flex h-full flex-col">
          <header className="flex flex-col gap-2 border-b border-outline-variant px-3 py-2.5 sm:flex-row sm:items-start sm:justify-between sm:gap-3 sm:px-4 sm:py-3">
            <div className="min-w-0 flex-1">
              <div className="text-base font-medium leading-snug">{scene.title}</div>
              <div className="mt-0.5 truncate text-sm text-dim">
                {scene.author} · {KIND_LABEL[scene.kind]}
                {scene.sol ? ` · sol ${scene.sol}` : ''} · {scene.license}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              autoFocus
              className="btn btn-tonal self-start sm:shrink-0"
            >
              Back to map
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
          <footer className="flex items-center justify-between gap-3 px-4 py-2 text-sm text-dim">
            <span className="truncate">
              {scene.renderer === 'sketchfab'
                ? `${scene.anchor} · External viewer: use Sketchfab's first-person mode.`
                : 'Drag to look around, WASD / arrows to walk.'}
            </span>
            <a href={scene.source} target="_blank" rel="noopener noreferrer" className="shrink-0 text-oxide underline hover:text-paper">
              Original source ↗
            </a>
          </footer>
        </div>
      )}
    </dialog>
  )
}

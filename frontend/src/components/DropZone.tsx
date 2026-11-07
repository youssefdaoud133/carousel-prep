import { ImagePlus } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

export const ACCEPTED = 'image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif'

/** Whole-window drag-and-drop target, shown while files are dragged over the page. */
export function WindowDrop({ onFiles }: { onFiles: (files: File[]) => void }) {
  const [active, setActive] = useState(false)
  const depth = useRef(0)

  useEffect(() => {
    const hasFiles = (e: DragEvent) => e.dataTransfer?.types.includes('Files') ?? false

    const enter = (e: DragEvent) => {
      if (!hasFiles(e)) return
      depth.current += 1
      setActive(true)
    }
    const leave = (e: DragEvent) => {
      if (!hasFiles(e)) return
      depth.current = Math.max(0, depth.current - 1)
      if (depth.current === 0) setActive(false)
    }
    const over = (e: DragEvent) => {
      if (hasFiles(e)) e.preventDefault()
    }
    const drop = (e: DragEvent) => {
      if (!hasFiles(e)) return
      e.preventDefault()
      depth.current = 0
      setActive(false)
      const files = Array.from(e.dataTransfer?.files ?? [])
      if (files.length) onFiles(files)
    }

    window.addEventListener('dragenter', enter)
    window.addEventListener('dragleave', leave)
    window.addEventListener('dragover', over)
    window.addEventListener('drop', drop)
    return () => {
      window.removeEventListener('dragenter', enter)
      window.removeEventListener('dragleave', leave)
      window.removeEventListener('dragover', over)
      window.removeEventListener('drop', drop)
    }
  }, [onFiles])

  if (!active) return null
  return (
    <div className="pointer-events-none fixed inset-0 z-40 grid place-items-center bg-table/85 p-6 backdrop-blur-sm">
      <div className="grid w-full max-w-xl place-items-center gap-3 rounded-2xl border-2 border-dashed border-marker bg-sheet px-8 py-16 text-center">
        <ImagePlus className="size-8 text-marker" aria-hidden />
        <p className="text-lg font-semibold">Drop photos to add them</p>
      </div>
    </div>
  )
}

/** Large empty-state target that also opens the file picker. */
export function EmptyDrop({ onBrowse }: { onBrowse: () => void }) {
  return (
    <button
      type="button"
      onClick={onBrowse}
      className="group grid w-full place-items-center gap-4 rounded-2xl border-2 border-dashed border-rule bg-sheet px-6 py-20 text-center transition-colors hover:border-marker"
    >
      <span className="grid size-14 place-items-center rounded-full bg-ig text-white">
        <ImagePlus className="size-6" aria-hidden />
      </span>
      <span className="space-y-1">
        <span className="block text-xl font-semibold tracking-tight">Drop your photos here</span>
        <span className="block text-graphite">
          or <span className="text-marker underline underline-offset-4">choose files</span>.
          JPG, PNG, WebP and HEIC work.
        </span>
      </span>
      <span className="max-w-md text-sm text-graphite">
        Portraits become one slide each. Landscapes are cut into two slides that line up when
        you swipe.
      </span>
    </button>
  )
}

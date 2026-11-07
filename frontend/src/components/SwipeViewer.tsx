import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { PreviewSlide } from '../api'

interface Props {
  slides: PreviewSlide[]
  start: number | null // slide index (0-based) to open at, null = closed
  onClose: () => void
}

/** One slide at a time, the way the carousel feels on a phone. */
export function SwipeViewer({ slides, start, onClose }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [index, setIndex] = useState(0)
  const pointerX = useRef<number | null>(null)

  useEffect(() => {
    const el = dialog.current
    if (!el) return
    if (start !== null && !el.open) el.showModal()
    if (start === null && el.open) el.close()
  }, [start])

  const [openedAt, setOpenedAt] = useState<number | null>(null)
  if (start !== openedAt) {
    setOpenedAt(start)
    if (start !== null) setIndex(start)
  }

  const last = slides.length - 1
  const go = (delta: number) => setIndex((i) => Math.min(last, Math.max(0, i + delta)))

  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      onClick={(e) => e.target === dialog.current && onClose()}
      onKeyDown={(e) => {
        if (e.key === 'ArrowRight') go(1)
        if (e.key === 'ArrowLeft') go(-1)
      }}
      aria-label="Carousel viewer"
      className="m-auto max-h-none max-w-none bg-transparent p-0 backdrop:bg-ink/85"
    >
      {start !== null && (
        <div className="flex flex-col items-center gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => go(-1)}
              disabled={index === 0}
              aria-label="Previous slide"
              className="rounded-full bg-sheet/15 p-2 text-white hover:bg-sheet/25 disabled:opacity-30"
            >
              <ChevronLeft className="size-5" aria-hidden />
            </button>

            <div
              className="w-[min(78vw,calc(80vh*0.8),440px)] touch-pan-y overflow-hidden rounded-lg bg-black select-none"
              onPointerDown={(e) => {
                pointerX.current = e.clientX
              }}
              onPointerUp={(e) => {
                if (pointerX.current === null) return
                const dx = e.clientX - pointerX.current
                pointerX.current = null
                if (Math.abs(dx) > 40) go(dx < 0 ? 1 : -1)
              }}
            >
              <div
                className="flex transition-transform duration-300 ease-out"
                style={{ transform: `translateX(-${index * 100}%)` }}
              >
                {slides.map((s) => (
                  <img
                    key={s.index}
                    src={s.data_url}
                    alt={`Slide ${s.index} of ${slides.length}`}
                    draggable={false}
                    className="aspect-4/5 w-full shrink-0"
                  />
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={() => go(1)}
              disabled={index === last}
              aria-label="Next slide"
              className="rounded-full bg-sheet/15 p-2 text-white hover:bg-sheet/25 disabled:opacity-30"
            >
              <ChevronRight className="size-5" aria-hidden />
            </button>
          </div>

          <div className="flex items-center gap-1.5" aria-hidden>
            {slides.map((s, i) => (
              <span
                key={s.index}
                className={`size-1.5 rounded-full transition-colors ${i === index ? 'bg-white' : 'bg-white/35'}`}
              />
            ))}
          </div>
          <p className="text-sm text-white/80" aria-live="polite">
            {index + 1} / {slides.length}
          </p>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close viewer"
            className="fixed right-4 top-4 rounded-full bg-sheet/15 p-2 text-white hover:bg-sheet/25"
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>
      )}
    </dialog>
  )
}

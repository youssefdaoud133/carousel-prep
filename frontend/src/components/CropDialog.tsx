import { useEffect, useRef } from 'react'
import type { FitMode } from '../api'
import type { Photo } from '../types'

const LANDSCAPE_RATIO = (2 * 1080) / 1350 // two slides side by side
const PORTRAIT_RATIO = 1080 / 1350

interface Props {
  photo: Photo | null
  fitMode: FitMode
  onFocusChange: (id: string, focus: number) => void
  onClose: () => void
}

/** Same math as backend `crop_box`, expressed as fractions of the photo. */
function cropWindow(w: number, h: number, ratio: number, focus: number) {
  if (w / h > ratio) {
    const cw = (h * ratio) / w
    return { x: (1 - cw) * focus, y: 0, w: cw, h: 1, axis: 'x' as const }
  }
  const ch = w / ratio / h
  return { x: 0, y: (1 - ch) * focus, w: 1, h: ch, axis: 'y' as const }
}

export function CropDialog({ photo, fitMode, onFocusChange, onClose }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const el = dialog.current
    if (!el) return
    if (photo && !el.open) el.showModal()
    if (!photo && el.open) el.close()
  }, [photo])

  const landscape = photo?.orientation === 'landscape'
  const padded = !landscape && fitMode === 'pad'
  const win = photo
    ? cropWindow(photo.width, photo.height, landscape ? LANDSCAPE_RATIO : PORTRAIT_RATIO, photo.focus)
    : null
  const fits = win ? win.w > 0.995 && win.h > 0.995 : false
  const adjustable = photo && win && !padded && !fits

  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      onClick={(e) => e.target === dialog.current && onClose()}
      aria-labelledby="crop-title"
      className="m-auto w-[min(92vw,560px)] rounded-2xl bg-sheet p-0 text-ink shadow-2xl ring-1 ring-rule backdrop:bg-ink/60"
    >
      {photo && win && (
        <div className="space-y-4 p-5">
          <div>
            <h2 id="crop-title" className="text-lg font-semibold tracking-tight">
              Adjust crop
            </h2>
            <p className="truncate text-sm text-graphite">{photo.filename}</p>
          </div>

          <div className="grid place-items-center rounded-xl bg-table p-3">
            <div className="relative max-h-[50vh] overflow-hidden">
              <img
                src={photo.thumbUrl}
                alt=""
                className="block max-h-[50vh] w-auto"
                style={{ aspectRatio: `${photo.width} / ${photo.height}` }}
              />
              {!padded && (
                <div
                  aria-hidden
                  className="absolute outline-2 outline-sheet transition-[left,top] duration-100"
                  style={{
                    left: `${win.x * 100}%`,
                    top: `${win.y * 100}%`,
                    width: `${win.w * 100}%`,
                    height: `${win.h * 100}%`,
                    boxShadow: '0 0 0 9999px rgb(0 0 0 / 0.55)',
                  }}
                >
                  {landscape && (
                    <span className="absolute inset-y-0 left-1/2 border-l-2 border-dashed border-marker" />
                  )}
                </div>
              )}
            </div>
          </div>

          {adjustable ? (
            <label className="block space-y-1.5">
              <span className="flex justify-between text-sm">
                <span>Crop position</span>
                <span className="text-graphite">
                  {win.axis === 'x' ? 'Left to right' : 'Top to bottom'}
                </span>
              </span>
              <input
                type="range"
                min={0}
                max={100}
                value={Math.round(photo.focus * 100)}
                onChange={(e) => onFocusChange(photo.id, Number(e.target.value) / 100)}
                className="w-full accent-marker"
              />
            </label>
          ) : (
            <p className="text-sm text-graphite">
              {padded
                ? 'This portrait is shown whole with a border, so nothing is cropped. Switch to "Crop to fill" to choose a crop.'
                : 'This photo already has the right shape, so nothing is cropped.'}
            </p>
          )}

          <div className="flex justify-end gap-2">
            {adjustable && (
              <button
                type="button"
                onClick={() => onFocusChange(photo.id, 0.5)}
                className="rounded-lg px-3 py-2 text-sm font-medium text-graphite hover:text-ink"
              >
                Center
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-sheet"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </dialog>
  )
}

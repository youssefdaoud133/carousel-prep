import type { PreviewSlide } from '../api'
import { slideName } from '../naming'

interface Props {
  slides: PreviewSlide[]
  slug: string
  updating: boolean
  onOpen: (position: number) => void
}

/**
 * Slides laid out in carousel order. Halves of a split landscape sit flush against each other
 * with a dashed seam marker, so you can check that the swipe reads as one picture.
 */
export function PreviewStrip({ slides, slug, updating, onOpen }: Props) {
  const groups: PreviewSlide[][] = []
  for (const slide of slides) {
    const last = groups.at(-1)
    if (slide.part === 'right' && last && last[0].image_id === slide.image_id) last.push(slide)
    else groups.push([slide])
  }

  return (
    <div
      className={`strip -mx-4 overflow-x-auto px-4 pb-3 transition-opacity sm:-mx-6 sm:px-6 ${
        updating ? 'opacity-60' : ''
      }`}
      aria-busy={updating}
    >
      <ol className="flex w-max gap-5">
        {groups.map((group) => (
          <li key={`${group[0].image_id}-${group[0].index}`} className="flex flex-col gap-2">
            <div className="relative flex shadow-sm ring-1 ring-rule">
              {group.map((slide) => (
                <button
                  key={slide.index}
                  type="button"
                  onClick={() => onOpen(slide.index - 1)}
                  aria-label={`View slide ${slide.index} full size`}
                  className="cursor-zoom-in focus-visible:z-10"
                >
                  <img
                    src={slide.data_url}
                    alt=""
                    className="block h-72 w-auto sm:h-80"
                    width={540}
                    height={675}
                  />
                </button>
              ))}
              {group.length === 2 && (
                <span
                  aria-hidden
                  className="pointer-events-none absolute inset-y-0 left-1/2 -translate-x-1/2 border-l-2 border-dashed border-marker/80"
                />
              )}
            </div>
            <div className="flex">
              {group.map((slide) => (
                <p
                  key={slide.index}
                  className="w-0 flex-1 truncate pr-2 text-xs text-graphite"
                  title={slug ? slideName(slug, slide.index) : undefined}
                >
                  <span className="font-semibold tabular-nums text-ink">{slide.index}</span>{' '}
                  {slug ? slideName(slug, slide.index) : 'Add a title to name files'}
                </p>
              ))}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

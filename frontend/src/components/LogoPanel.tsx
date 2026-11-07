import { ImageUp, LoaderCircle, Trash2 } from 'lucide-react'
import { useRef } from 'react'
import type { Corner, LogoOptions } from '../api'

interface Props {
  options: LogoOptions
  onChange: (options: LogoOptions) => void
  previewUrl: string | null
  uploading: boolean
  onUpload: (file: File) => void
  onRemove: () => void
}

const CORNERS: { value: Corner; label: string; className: string }[] = [
  { value: 'top-left', label: 'Top left', className: 'left-1.5 top-1.5' },
  { value: 'top-right', label: 'Top right', className: 'right-1.5 top-1.5' },
  { value: 'bottom-left', label: 'Bottom left', className: 'bottom-1.5 left-1.5' },
  { value: 'bottom-right', label: 'Bottom right', className: 'bottom-1.5 right-1.5' },
]

export function LogoPanel({ options, onChange, previewUrl, uploading, onUpload, onRemove }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const set = (patch: Partial<LogoOptions>) => onChange({ ...options, ...patch })

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h2 id="logo-heading" className="font-semibold">
          Logo
        </h2>
        <button
          type="button"
          role="switch"
          aria-checked={options.enabled}
          aria-labelledby="logo-heading"
          onClick={() => set({ enabled: !options.enabled })}
          className={`relative h-6 w-11 rounded-full transition-colors ${
            options.enabled ? 'bg-ig' : 'bg-rule'
          }`}
        >
          <span
            className={`absolute top-0.5 size-5 rounded-full bg-white shadow transition-[left] ${
              options.enabled ? 'left-5.5' : 'left-0.5'
            }`}
          />
        </button>
      </div>

      <input
        ref={input}
        type="file"
        accept="image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          e.target.value = ''
          if (file) onUpload(file)
        }}
      />

      {!options.enabled ? (
        <p className="text-sm text-graphite">Turn on to place a logo in a corner of every slide.</p>
      ) : !previewUrl ? (
        <button
          type="button"
          onClick={() => input.current?.click()}
          disabled={uploading}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-rule px-3 py-4 text-sm text-graphite transition-colors hover:border-marker hover:text-marker"
        >
          {uploading ? (
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
          ) : (
            <ImageUp className="size-4" aria-hidden />
          )}
          {uploading ? 'Uploading logo…' : 'Choose a PNG logo'}
        </button>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="grid h-14 w-20 shrink-0 place-items-center rounded-md bg-[repeating-conic-gradient(var(--color-rule)_0_25%,transparent_0_50%)] bg-size-[12px_12px] ring-1 ring-rule">
              <img src={previewUrl} alt="Your logo" className="max-h-12 max-w-18 object-contain" />
            </div>
            <div className="flex flex-col items-start gap-1 text-sm">
              <button
                type="button"
                onClick={() => input.current?.click()}
                className="font-medium text-ink hover:text-marker"
              >
                Replace logo
              </button>
              <button
                type="button"
                onClick={onRemove}
                className="inline-flex items-center gap-1 text-graphite hover:text-danger"
              >
                <Trash2 className="size-3.5" aria-hidden />
                Remove
              </button>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div
              role="radiogroup"
              aria-label="Logo corner"
              className="relative aspect-4/5 w-20 shrink-0 rounded-md bg-well ring-1 ring-rule"
            >
              {CORNERS.map((c) => {
                const active = options.corner === c.value
                return (
                  <button
                    key={c.value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    aria-label={c.label}
                    title={c.label}
                    onClick={() => set({ corner: c.value })}
                    className={`absolute size-5 rounded-sm transition-colors ${c.className} ${
                      active ? 'bg-ig' : 'bg-rule hover:bg-graphite/50'
                    }`}
                  />
                )
              })}
            </div>
            <p className="text-sm text-graphite">
              {CORNERS.find((c) => c.value === options.corner)?.label} corner. On split landscapes
              it appears once, on the {options.corner.endsWith('left') ? 'first' : 'second'} half.
            </p>
          </div>

          <Slider
            label="Size"
            value={options.size_pct}
            min={5}
            max={40}
            unit="% of width"
            onChange={(v) => set({ size_pct: v })}
          />
          <Slider
            label="Margin"
            value={options.margin_pct}
            min={0}
            max={15}
            unit="%"
            onChange={(v) => set({ margin_pct: v })}
          />
          <Slider
            label="Opacity"
            value={options.opacity}
            min={10}
            max={100}
            unit="%"
            onChange={(v) => set({ opacity: v })}
          />
        </div>
      )}
    </section>
  )
}

function Slider({
  label,
  value,
  min,
  max,
  unit,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  unit: string
  onChange: (value: number) => void
}) {
  return (
    <label className="block space-y-1">
      <span className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="tabular-nums text-graphite">
          {value}
          {unit}
        </span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-marker"
      />
    </label>
  )
}

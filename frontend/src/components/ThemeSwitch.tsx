import { Monitor, Moon, Sun } from 'lucide-react'
import type { ThemeChoice } from '../hooks/useTheme'

const OPTIONS: { value: ThemeChoice; label: string; Icon: typeof Sun }[] = [
  { value: 'system', label: 'Match system', Icon: Monitor },
  { value: 'light', label: 'Light', Icon: Sun },
  { value: 'dark', label: 'Dark', Icon: Moon },
]

export function ThemeSwitch({
  value,
  onChange,
}: {
  value: ThemeChoice
  onChange: (value: ThemeChoice) => void
}) {
  return (
    <div role="radiogroup" aria-label="Theme" className="flex rounded-full bg-well p-0.5">
      {OPTIONS.map(({ value: v, label, Icon }) => {
        const active = v === value
        return (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={label}
            title={label}
            onClick={() => onChange(v)}
            className={`grid size-7 place-items-center rounded-full transition-colors ${
              active ? 'bg-sheet text-marker shadow-sm' : 'text-graphite hover:text-ink'
            }`}
          >
            <Icon className="size-3.5" aria-hidden />
          </button>
        )
      })}
    </div>
  )
}

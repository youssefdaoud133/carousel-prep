import { CircleAlert, CircleCheck, X } from 'lucide-react'
import type { Toast } from '../hooks/useToasts'

export function Toasts({ toasts, dismiss }: { toasts: Toast[]; dismiss: (id: number) => void }) {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4">
      {toasts.map((t) => (
        <div
          key={t.id}
          role={t.kind === 'error' ? 'alert' : 'status'}
          className="pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-xl bg-ink px-4 py-3 text-sheet shadow-lg"
        >
          {t.kind === 'error' ? (
            <CircleAlert className="mt-0.5 size-4 shrink-0 text-marker" aria-hidden />
          ) : (
            <CircleCheck className="mt-0.5 size-4 shrink-0 text-ok" aria-hidden />
          )}
          <p className="flex-1 text-sm">{t.message}</p>
          <button
            type="button"
            onClick={() => dismiss(t.id)}
            className="rounded p-0.5 opacity-70 hover:opacity-100"
            aria-label="Dismiss"
          >
            <X className="size-4" aria-hidden />
          </button>
        </div>
      ))}
    </div>
  )
}

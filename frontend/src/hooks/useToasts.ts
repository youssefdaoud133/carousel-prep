import { useCallback, useState } from 'react'

export type ToastKind = 'error' | 'success' | 'info'

export interface Toast {
  id: number
  kind: ToastKind
  message: string
}

let nextId = 1

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((all) => all.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (kind: ToastKind, message: string) => {
      const id = nextId++
      setToasts((all) => [...all.slice(-3), { id, kind, message }])
      window.setTimeout(() => dismiss(id), kind === 'error' ? 8000 : 4000)
    },
    [dismiss],
  )

  return { toasts, push, dismiss }
}

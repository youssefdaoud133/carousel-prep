import { useCallback, useEffect, useState, useSyncExternalStore } from 'react'

export type ThemeChoice = 'system' | 'light' | 'dark'

const STORAGE_KEY = 'theme'
const darkQuery = '(prefers-color-scheme: dark)'

function readChoice(): ThemeChoice {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch {
    // storage unavailable (private mode, blocked site data)
  }
  return 'system'
}

function subscribeToOs(onChange: () => void) {
  const mq = window.matchMedia(darkQuery)
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
}

const osPrefersDark = () => window.matchMedia(darkQuery).matches

/** Theme choice (saved per browser) and the theme actually shown. */
export function useTheme() {
  const [choice, setChoiceState] = useState<ThemeChoice>(readChoice)
  const osDark = useSyncExternalStore(subscribeToOs, osPrefersDark)
  const resolved: 'light' | 'dark' = choice === 'system' ? (osDark ? 'dark' : 'light') : choice

  useEffect(() => {
    const root = document.documentElement
    if (choice === 'system') delete root.dataset.theme
    else root.dataset.theme = choice
  }, [choice])

  const setChoice = useCallback((next: ThemeChoice) => {
    setChoiceState(next)
    try {
      if (next === 'system') localStorage.removeItem(STORAGE_KEY)
      else localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // the choice still applies for this visit
    }
  }, [])

  return { choice, resolved, setChoice }
}

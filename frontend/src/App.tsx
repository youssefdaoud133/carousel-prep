import { useEffect, useState } from 'react'

export default function App() {
  const [api, setApi] = useState<'checking' | 'ok' | 'down'>('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => setApi(r.ok ? 'ok' : 'down'))
      .catch(() => setApi('down'))
  }, [])

  return (
    <main className="min-h-screen grid place-items-center bg-neutral-50 text-neutral-900">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Carousel Prep</h1>
        <p className="text-neutral-500">Instagram carousel photo preparation</p>
        <p className="text-sm">
          API:{' '}
          <span className={api === 'ok' ? 'text-emerald-600' : api === 'down' ? 'text-red-600' : 'text-neutral-400'}>
            {api}
          </span>
        </p>
      </div>
    </main>
  )
}

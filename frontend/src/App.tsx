import { Download, LoaderCircle, TriangleAlert } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  api,
  ApiError,
  type FitMode,
  type LogoOptions,
  type PadColor,
  type PreviewSlide,
  type RenderRequest,
} from './api'
import { ACCEPTED, EmptyDrop, WindowDrop } from './components/DropZone'
import { CropDialog } from './components/CropDialog'
import { LogoPanel } from './components/LogoPanel'
import { PhotoList } from './components/PhotoList'
import { PreviewStrip } from './components/PreviewStrip'
import { Segmented } from './components/Segmented'
import { SwipeViewer } from './components/SwipeViewer'
import { Toasts } from './components/Toasts'
import { useToasts } from './hooks/useToasts'
import { slideName, slugify } from './naming'
import type { Photo } from './types'
import brandMarkDark from './assets/logo-dark.png'
import brandMark from './assets/logo.png'

const INSTAGRAM_MAX_SLIDES = 20
const UPLOAD_CONCURRENCY = 3

const DEFAULT_LOGO: LogoOptions = {
  enabled: false,
  corner: 'bottom-right',
  size_pct: 15,
  margin_pct: 4,
  opacity: 100,
}

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [photos, setPhotos] = useState<Photo[]>([])
  const [pending, setPending] = useState<{ key: string; name: string }[]>([])
  const [title, setTitle] = useState('')
  const [fitMode, setFitMode] = useState<FitMode>('crop')
  const [padColor, setPadColor] = useState<PadColor>('white')
  const [logo, setLogo] = useState<LogoOptions>(DEFAULT_LOGO)
  const [logoUrl, setLogoUrl] = useState<string | null>(null)
  const [logoUploading, setLogoUploading] = useState(false)
  const [rendered, setRendered] = useState<{ key: string; slides: PreviewSlide[] }>({
    key: '',
    slides: [],
  })
  const [exporting, setExporting] = useState(false)
  const [cropId, setCropId] = useState<string | null>(null)
  const [viewerStart, setViewerStart] = useState<number | null>(null)
  const [startError, setStartError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const { toasts, push, dismiss } = useToasts()

  const slug = slugify(title)
  const slideCount = photos.reduce((n, p) => n + p.slides, 0)

  // --- session -------------------------------------------------------------

  const startSession = useCallback(() => {
    api.createSession().then(
      (id) => {
        setSessionId(id)
        setStartError(null)
      },
      (err: unknown) => {
        setStartError(err instanceof Error ? err.message : 'Cannot reach the server.')
      },
    )
  }, [])

  useEffect(startSession, [startSession])

  const handleError = useCallback(
    (err: unknown) => {
      if (err instanceof DOMException && err.name === 'AbortError') return
      if (err instanceof ApiError && err.sessionExpired) {
        setPhotos([])
        setLogoUrl((url) => {
          if (url) URL.revokeObjectURL(url)
          return null
        })
        push('error', 'Your session expired after 2 hours without activity. Add your photos again.')
        startSession()
        return
      }
      push('error', err instanceof Error ? err.message : 'Something went wrong.')
    },
    [push, startSession],
  )

  // --- uploads -------------------------------------------------------------

  const addFiles = useCallback(
    async (files: File[]) => {
      if (!sessionId) return
      const batch = files.map((file, i) => ({ file, key: `${Date.now()}-${i}`, name: file.name }))
      setPending((p) => [...p, ...batch.map(({ key, name }) => ({ key, name }))])

      // Upload a few at a time, but add finished photos in the order they were chosen.
      const results: (Photo[] | null)[] = new Array(batch.length).fill(undefined)
      let committed = 0
      const commit = () => {
        while (committed < batch.length && results[committed] !== undefined) {
          const done = results[committed]
          const key = batch[committed].key
          setPending((p) => p.filter((x) => x.key !== key))
          if (done) setPhotos((p) => [...p, ...done])
          committed += 1
        }
      }

      let cursor = 0
      const worker = async () => {
        while (cursor < batch.length) {
          const i = cursor++
          const { file } = batch[i]
          try {
            const res = await api.uploadImage(sessionId, file)
            for (const e of res.errors) push('error', `${e.filename}: ${e.message}`)
            results[i] = res.images.map((img) => ({
              ...img,
              focus: 0.5,
              thumbUrl: api.thumbUrl(sessionId, img.id),
            }))
          } catch (err) {
            results[i] = null
            handleError(err)
          }
          commit()
        }
      }
      await Promise.all(Array.from({ length: UPLOAD_CONCURRENCY }, worker))
    },
    [sessionId, push, handleError],
  )

  const openPicker = () => fileInput.current?.click()

  async function removePhoto(id: string) {
    if (!sessionId) return
    setPhotos((p) => p.filter((x) => x.id !== id))
    try {
      await api.deleteImage(sessionId, id)
    } catch (err) {
      handleError(err)
    }
  }

  // --- logo ----------------------------------------------------------------

  async function uploadLogo(file: File) {
    if (!sessionId) return
    setLogoUploading(true)
    try {
      await api.uploadLogo(sessionId, file)
      setLogoUrl((old) => {
        if (old) URL.revokeObjectURL(old)
        return URL.createObjectURL(file)
      })
      setLogo((l) => ({ ...l, enabled: true }))
    } catch (err) {
      handleError(err)
    } finally {
      setLogoUploading(false)
    }
  }

  async function removeLogo() {
    if (!sessionId) return
    setLogoUrl((old) => {
      if (old) URL.revokeObjectURL(old)
      return null
    })
    try {
      await api.deleteLogo(sessionId)
    } catch (err) {
      handleError(err)
    }
  }

  // --- preview -------------------------------------------------------------

  const renderRequest = useMemo<RenderRequest>(
    () => ({
      order: photos.map((p) => ({ id: p.id, focus: p.focus })),
      fit_mode: fitMode,
      pad_color: padColor,
      logo: { ...logo, enabled: logo.enabled && logoUrl !== null },
    }),
    [photos, fitMode, padColor, logo, logoUrl],
  )

  // The preview is "updating" whenever the latest settings differ from what was last rendered.
  const requestKey = JSON.stringify(renderRequest)
  const hasPhotos = renderRequest.order.length > 0
  const slides = hasPhotos ? rendered.slides : []
  const updating = hasPhotos && rendered.key !== requestKey

  useEffect(() => {
    if (!sessionId || renderRequest.order.length === 0) return
    const controller = new AbortController()
    const timer = window.setTimeout(async () => {
      try {
        const next = await api.preview(sessionId, renderRequest, controller.signal)
        setRendered({ key: requestKey, slides: next })
      } catch (err) {
        if (controller.signal.aborted) return
        setRendered((r) => ({ ...r, key: requestKey }))
        handleError(err)
      }
    }, 250)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [sessionId, renderRequest, requestKey, handleError])

  // --- export --------------------------------------------------------------

  const exportBlocker =
    photos.length === 0
      ? 'Add photos to export'
      : !slug
        ? 'Add a post title to export'
        : pending.length > 0
          ? 'Wait for uploads to finish'
          : null

  async function exportZip() {
    if (!sessionId || exportBlocker) return
    setExporting(true)
    try {
      const { blob, filename } = await api.exportZip(sessionId, { ...renderRequest, title })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
      push('success', `Downloaded ${filename} with ${slideCount} slides.`)
    } catch (err) {
      handleError(err)
    } finally {
      setExporting(false)
    }
  }

  // --- layout --------------------------------------------------------------

  return (
    <div className="min-h-screen">
      <WindowDrop onFiles={addFiles} />
      <input
        ref={fileInput}
        type="file"
        multiple
        accept={ACCEPTED}
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? [])
          e.target.value = ''
          if (files.length) void addFiles(files)
        }}
      />

      <header className="sticky top-0 z-30 border-b border-rule bg-table/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <picture>
              <source srcSet={brandMarkDark} media="(prefers-color-scheme: dark)" />
              <img src={brandMark} alt="" width={35} height={28} className="h-7 w-auto" />
            </picture>
            <span className="text-lg font-semibold tracking-tight">Carousel Prep</span>
          </div>
          <div className="ml-auto flex items-center gap-3">
            {exportBlocker && photos.length > 0 && (
              <span className="hidden text-sm text-graphite sm:inline">{exportBlocker}</span>
            )}
            <button
              type="button"
              onClick={exportZip}
              disabled={!!exportBlocker || exporting}
              title={exportBlocker ?? undefined}
              className="inline-flex items-center gap-2 rounded-lg bg-marker px-4 py-2 text-sm font-semibold text-marker-ink shadow-sm transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100"
            >
              {exporting ? (
                <LoaderCircle className="size-4 animate-spin" aria-hidden />
              ) : (
                <Download className="size-4" aria-hidden />
              )}
              {exporting ? 'Exporting…' : 'Export ZIP'}
            </button>
          </div>
        </div>
      </header>

      {startError && (
        <div role="alert" className="mx-auto mt-6 max-w-7xl px-4 sm:px-6">
          <div className="flex items-center gap-3 rounded-xl border border-danger/40 bg-sheet px-4 py-3 text-sm">
            <TriangleAlert className="size-4 shrink-0 text-danger" aria-hidden />
            <span className="flex-1">{startError}</span>
            <button
              type="button"
              onClick={startSession}
              className="font-semibold text-marker underline underline-offset-4"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      <main className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[320px_minmax(0,1fr)] lg:items-start">
        <aside className="space-y-6 rounded-2xl bg-sheet p-5 ring-1 ring-rule lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto">
          <section className="space-y-2">
            <label htmlFor="title" className="block font-semibold">
              Post title
            </label>
            <input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Lisbon weekend"
              maxLength={120}
              className="w-full rounded-lg border border-rule bg-sheet px-3 py-2 placeholder:text-graphite/70 focus:border-marker focus:outline-none"
            />
            <p className="text-sm text-graphite">
              {slug ? (
                <>
                  Files are named <span className="text-ink">{slideName(slug, 1)}</span>,{' '}
                  {slideName(slug, 2).replace(`${slug}_`, '')} and so on.
                </>
              ) : title.trim() ? (
                'Use at least one letter or digit.'
              ) : (
                'Used for the file names and the ZIP folder.'
              )}
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold">Portrait photos</h2>
            <Segmented
              label="Portrait photos"
              value={fitMode}
              onChange={setFitMode}
              options={[
                { value: 'crop', label: 'Crop to fill' },
                { value: 'pad', label: 'Fit with border' },
              ]}
            />
            {fitMode === 'pad' && (
              <Segmented
                label="Border"
                value={padColor}
                onChange={setPadColor}
                options={[
                  { value: 'white', label: 'White' },
                  { value: 'black', label: 'Black' },
                  { value: 'blur', label: 'Blur' },
                ]}
              />
            )}
            <p className="text-sm text-graphite">
              Every slide is 1080 × 1350 (4:5). Landscapes are always cropped so their two halves
              fill the frame.
            </p>
          </section>

          <LogoPanel
            options={logo}
            onChange={setLogo}
            previewUrl={logoUrl}
            uploading={logoUploading}
            onUpload={uploadLogo}
            onRemove={removeLogo}
          />
        </aside>

        <div className="min-w-0 space-y-8">
          {photos.length === 0 && pending.length === 0 ? (
            <EmptyDrop onBrowse={openPicker} />
          ) : (
            <>
              <section className="space-y-3">
                <div className="flex items-baseline justify-between gap-4">
                  <h2 className="text-lg font-semibold tracking-tight">Photos</h2>
                  <p className="text-sm text-graphite">Drag to change the carousel order</p>
                </div>
                <PhotoList
                  photos={photos}
                  pending={pending}
                  onReorder={setPhotos}
                  onRemove={removePhoto}
                  onAdjust={setCropId}
                  onAdd={openPicker}
                />
              </section>

              <section className="space-y-3">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <h2 className="flex items-center gap-2 text-lg font-semibold tracking-tight">
                    Preview
                    {updating && (
                      <LoaderCircle
                        className="size-4 animate-spin text-graphite"
                        aria-label="Updating preview"
                      />
                    )}
                  </h2>
                  <p
                    className={`text-sm ${slideCount > INSTAGRAM_MAX_SLIDES ? 'text-danger' : 'text-graphite'}`}
                  >
                    {slideCount} {slideCount === 1 ? 'slide' : 'slides'}
                    {slideCount > INSTAGRAM_MAX_SLIDES &&
                      `. Instagram allows up to ${INSTAGRAM_MAX_SLIDES} per post.`}
                  </p>
                </div>
                {slides.length > 0 ? (
                  <PreviewStrip
                    slides={slides}
                    slug={slug}
                    updating={updating}
                    onOpen={setViewerStart}
                  />
                ) : (
                  <div className="grid h-72 place-items-center rounded-xl border border-dashed border-rule text-sm text-graphite">
                    {updating || pending.length ? 'Rendering preview…' : 'No slides yet'}
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </main>

      <CropDialog
        photo={photos.find((p) => p.id === cropId) ?? null}
        fitMode={fitMode}
        onFocusChange={(id, focus) =>
          setPhotos((all) => all.map((p) => (p.id === id ? { ...p, focus } : p)))
        }
        onClose={() => setCropId(null)}
      />
      <SwipeViewer slides={slides} start={viewerStart} onClose={() => setViewerStart(null)} />
      <Toasts toasts={toasts} dismiss={dismiss} />
    </div>
  )
}

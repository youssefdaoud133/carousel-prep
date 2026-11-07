export type Orientation = 'portrait' | 'landscape'
export type FitMode = 'crop' | 'pad'
export type PadColor = 'white' | 'black' | 'blur'
export type Corner = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
export type SlidePart = 'full' | 'left' | 'right'

export interface ImageInfo {
  id: string
  filename: string
  width: number
  height: number
  orientation: Orientation
  slides: number
}

export interface UploadResult {
  images: ImageInfo[]
  errors: { filename: string; message: string }[]
}

export interface LogoOptions {
  enabled: boolean
  corner: Corner
  size_pct: number
  margin_pct: number
  opacity: number
}

export interface RenderRequest {
  order: { id: string; focus: number }[]
  fit_mode: FitMode
  pad_color: PadColor
  logo: LogoOptions
  title?: string
}

export interface PreviewSlide {
  index: number
  image_id: string
  part: SlidePart
  data_url: string
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }

  get sessionExpired(): boolean {
    return this.status === 404 && this.message.startsWith('Session')
  }
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return 'Some settings are invalid. Reset them and try again.'
  } catch {
    // not JSON
  }
  if (res.status === 413) return 'The file is too large to upload.'
  if (res.status >= 500) return 'The server hit a problem. Try again in a moment.'
  return `Request failed (${res.status})`
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, init)
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(0, 'Cannot reach the server. Check that the app is running.')
  }
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res))
  return res
}

const json = (body: unknown, signal?: AbortSignal): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
  signal,
})

function fileForm(field: string, file: File): FormData {
  const form = new FormData()
  form.append(field, file)
  return form
}

function filenameFrom(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback
  const star = /filename\*=UTF-8''([^;]+)/i.exec(disposition)
  if (star) return decodeURIComponent(star[1])
  const plain = /filename="([^"]+)"/i.exec(disposition)
  return plain ? plain[1] : fallback
}

export const api = {
  async createSession(): Promise<string> {
    const res = await request('/sessions', { method: 'POST' })
    return (await res.json()).id
  },

  async uploadImage(sessionId: string, file: File): Promise<UploadResult> {
    const res = await request(`/sessions/${sessionId}/images`, {
      method: 'POST',
      body: fileForm('files', file),
    })
    return res.json()
  },

  thumbUrl(sessionId: string, imageId: string): string {
    return `/api/sessions/${sessionId}/images/${imageId}/thumb`
  },

  async deleteImage(sessionId: string, imageId: string): Promise<void> {
    await request(`/sessions/${sessionId}/images/${imageId}`, { method: 'DELETE' })
  },

  async uploadLogo(sessionId: string, file: File): Promise<{ width: number; height: number }> {
    const res = await request(`/sessions/${sessionId}/logo`, {
      method: 'PUT',
      body: fileForm('file', file),
    })
    return res.json()
  },

  async deleteLogo(sessionId: string): Promise<void> {
    await request(`/sessions/${sessionId}/logo`, { method: 'DELETE' })
  },

  async preview(sessionId: string, req: RenderRequest, signal?: AbortSignal): Promise<PreviewSlide[]> {
    const res = await request(`/sessions/${sessionId}/preview`, json(req, signal))
    return (await res.json()).slides
  },

  async exportZip(sessionId: string, req: RenderRequest): Promise<{ blob: Blob; filename: string }> {
    const res = await request(`/sessions/${sessionId}/export`, json(req))
    const filename = filenameFrom(res.headers.get('Content-Disposition'), 'carousel.zip')
    return { blob: await res.blob(), filename }
  },
}

/**
 * Mirrors backend `slugify` so filenames update instantly while typing.
 * The server stays authoritative for the exported names.
 */
export function slugify(title: string): string {
  let text = title.normalize('NFC').trim().toLowerCase()
  text = text.replace(/[^\p{L}\p{N}_-]+/gu, '_')
  text = text.replace(/[-_]*_[-_]*/g, '_')
  text = text.replace(/-{2,}/g, '-')
  text = trimSeparators(trimSeparators(text).slice(0, 80))
  return text
}

function trimSeparators(text: string): string {
  return text.replace(/^[_-]+|[_-]+$/g, '')
}

export function slideName(slug: string, index: number): string {
  return `${slug}_picture_${index}.jpg`
}

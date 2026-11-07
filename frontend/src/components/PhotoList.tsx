import {
  type Announcements,
  closestCenter,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  type UniqueIdentifier,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  arrayMove,
  rectSortingStrategy,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Crop, ImagePlus, LoaderCircle, X } from 'lucide-react'
import type { Photo } from '../types'

interface Props {
  photos: Photo[]
  pending: { key: string; name: string }[]
  onReorder: (photos: Photo[]) => void
  onRemove: (id: string) => void
  onAdjust: (id: string) => void
  onAdd: () => void
}

export function PhotoList({ photos, pending, onReorder, onRemove, onAdjust, onAdd }: Props) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const nameOf = (id: UniqueIdentifier) => photos.find((p) => p.id === id)?.filename ?? 'Photo'
  const positionOf = (id: UniqueIdentifier) => photos.findIndex((p) => p.id === id) + 1
  const announcements: Announcements = {
    onDragStart: ({ active }) => `Picked up ${nameOf(active.id)}.`,
    onDragOver: ({ active, over }) =>
      over ? `${nameOf(active.id)} is over position ${positionOf(over.id)}.` : undefined,
    onDragEnd: ({ active, over }) =>
      over
        ? `${nameOf(active.id)} moved to position ${positionOf(over.id)}.`
        : `${nameOf(active.id)} dropped.`,
    onDragCancel: ({ active }) => `Moving ${nameOf(active.id)} was cancelled.`,
  }

  function handleDragEnd({ active, over }: DragEndEvent) {
    if (!over || active.id === over.id) return
    const from = photos.findIndex((p) => p.id === active.id)
    const to = photos.findIndex((p) => p.id === over.id)
    onReorder(arrayMove(photos, from, to))
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
      accessibility={{ announcements }}
    >
      <SortableContext items={photos.map((p) => p.id)} strategy={rectSortingStrategy}>
        <ul className="grid grid-cols-[repeat(auto-fill,minmax(112px,1fr))] gap-3">
          {photos.map((photo, i) => (
            <PhotoCard
              key={photo.id}
              photo={photo}
              position={i + 1}
              onRemove={onRemove}
              onAdjust={onAdjust}
            />
          ))}
          {pending.map((p) => (
            <li
              key={p.key}
              className="flex aspect-square flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-rule text-graphite"
            >
              <LoaderCircle className="size-5 animate-spin" aria-hidden />
              <span className="w-full truncate px-2 text-center text-xs">{p.name}</span>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={onAdd}
              className="flex aspect-square w-full flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed border-rule text-sm text-graphite transition-colors hover:border-marker hover:text-marker"
            >
              <ImagePlus className="size-5" aria-hidden />
              Add photos
            </button>
          </li>
        </ul>
      </SortableContext>
    </DndContext>
  )
}

function PhotoCard({
  photo,
  position,
  onRemove,
  onAdjust,
}: {
  photo: Photo
  position: number
  onRemove: (id: string) => void
  onAdjust: (id: string) => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: photo.id,
  })
  const split = photo.orientation === 'landscape'

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`group relative ${isDragging ? 'z-10 opacity-80' : ''}`}
    >
      <div
        {...attributes}
        {...listeners}
        aria-label={`${photo.filename}, position ${position}. Press space to move it.`}
        className={`relative aspect-square cursor-grab touch-none overflow-hidden rounded-lg bg-sheet ring-1 ring-rule active:cursor-grabbing ${
          isDragging ? 'shadow-xl ring-marker' : ''
        }`}
      >
        <img
          src={photo.thumbUrl}
          alt=""
          draggable={false}
          className="size-full object-contain"
        />
        {split && (
          <span
            aria-hidden
            className="absolute inset-y-1 left-1/2 border-l border-dashed border-seam"
          />
        )}
        <span className="absolute left-1.5 top-1.5 rounded bg-ink/80 px-1.5 text-xs font-medium tabular-nums text-sheet">
          {position}
        </span>
      </div>
      <div className="mt-1 flex items-baseline justify-between gap-2 text-xs">
        <span className="truncate text-graphite" title={photo.filename}>
          {photo.filename}
        </span>
        {split && <span className="shrink-0 text-marker">2 slides</span>}
      </div>
      <div className="absolute right-1.5 top-1.5 flex gap-1 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100 pointer-coarse:opacity-100">
        <button
          type="button"
          onClick={() => onAdjust(photo.id)}
          aria-label={`Adjust crop of ${photo.filename}`}
          title="Adjust crop"
          className="rounded-full bg-ink/80 p-1 text-sheet hover:bg-ink"
        >
          <Crop className="size-3.5" aria-hidden />
        </button>
        <button
          type="button"
          onClick={() => onRemove(photo.id)}
          aria-label={`Remove ${photo.filename}`}
          title="Remove"
          className="rounded-full bg-ink/80 p-1 text-sheet hover:bg-ink"
        >
          <X className="size-3.5" aria-hidden />
        </button>
      </div>
    </li>
  )
}

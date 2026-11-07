import type { ImageInfo } from './api'

export interface Photo extends ImageInfo {
  thumbUrl: string
  focus: number // 0..1 crop window position
}

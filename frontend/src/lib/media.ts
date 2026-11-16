// Browser-side media preparation (phase 3, task 3).
export const MAX_SIDE = 1600
export const JPEG_QUALITY = 0.8
export const MAX_VIDEO_BYTES = 50 * 1024 * 1024
export const MAX_VIDEO_SECONDS = 60

/** Resize to 1600 px on the longest side and re-encode as JPEG 0.8. Re-encoding drops EXIF and GPS. */
export async function resizePhoto(file: File): Promise<Blob> {
  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' } as any)
  } catch {
    bitmap = await createImageBitmap(file)
  }
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height))
  const w = Math.round(bitmap.width * scale)
  const h = Math.round(bitmap.height * scale)
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(bitmap, 0, 0, w, h)
  bitmap.close?.()
  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('resize failed'))), 'image/jpeg', JPEG_QUALITY),
  )
}

export function videoDuration(file: File): Promise<number> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const v = document.createElement('video')
    v.preload = 'metadata'
    v.onloadedmetadata = () => {
      URL.revokeObjectURL(url)
      resolve(v.duration || 0)
    }
    v.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(0)
    }
    v.src = url
  })
}

/** Returns an Arabic error message when the video is over the limits, otherwise null. */
export async function checkVideo(file: File): Promise<string | null> {
  if (file.size > MAX_VIDEO_BYTES) return 'الفيديو أكبر من 50 ميجا. صوّر فيديو أقصر أو قصّه قبل الرفع.'
  const seconds = await videoDuration(file)
  if (seconds > MAX_VIDEO_SECONDS) return 'الفيديو أطول من دقيقة. صوّر فيديو أقصر أو قصّه قبل الرفع.'
  return null
}

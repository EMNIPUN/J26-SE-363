export const PICTURE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const PICTURE_SIZE = 256
// What a person may pick. It is shrunk to a small square before it is sent, so this is generous.
const MAX_PICKED_BYTES = 15 * 1024 * 1024

/** A message for a file that cannot be used as a picture, or null when it can. */
export function checkPictureFile(file) {
  if (!file) return 'Choose a picture.'
  if (!PICTURE_TYPES.includes(file.type)) return 'Use a JPG, PNG or WebP picture.'
  if (file.size > MAX_PICKED_BYTES) return 'That picture is too large (15 MB at most).'
  return null
}

/** The biggest centred square in a picture of this size: where it starts and its side. */
export function centredSquare(width, height) {
  const side = Math.min(width, height)
  return { x: Math.floor((width - side) / 2), y: Math.floor((height - side) / 2), side }
}

/** A square JPEG of the picture, cut from the middle and shrunk to PICTURE_SIZE. */
export async function squarePicture(file, size = PICTURE_SIZE) {
  let bitmap
  try {
    bitmap = await createImageBitmap(file)
  } catch {
    throw new Error('That file could not be read as a picture.')
  }
  const { x, y, side } = centredSquare(bitmap.width, bitmap.height)
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')
  context.fillStyle = '#ffffff' // a transparent PNG gets a white background, not black
  context.fillRect(0, 0, size, size)
  context.drawImage(bitmap, x, y, side, side, 0, 0, size, size)
  bitmap.close?.()
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85))
  if (!blob) throw new Error('That picture could not be prepared.')
  return blob
}

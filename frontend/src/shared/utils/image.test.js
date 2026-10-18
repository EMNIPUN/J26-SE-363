import { describe, expect, it } from 'vitest'
import { centredSquare, checkPictureFile } from './image.js'

describe('checkPictureFile', () => {
  it('accepts JPEG, PNG and WebP', () => {
    for (const type of ['image/jpeg', 'image/png', 'image/webp']) {
      expect(checkPictureFile({ type, size: 1000 })).toBeNull()
    }
  })

  it('refuses other files', () => {
    for (const type of ['image/gif', 'image/svg+xml', 'application/pdf', '']) {
      expect(checkPictureFile({ type, size: 1000 })).toMatch(/JPG, PNG or WebP/)
    }
  })

  it('refuses a huge file and no file', () => {
    expect(checkPictureFile({ type: 'image/png', size: 20 * 1024 * 1024 })).toMatch(/too large/)
    expect(checkPictureFile(null)).toBe('Choose a picture.')
  })
})

describe('centredSquare', () => {
  it('cuts the middle of a wide picture', () => {
    expect(centredSquare(400, 200)).toEqual({ x: 100, y: 0, side: 200 })
  })

  it('cuts the middle of a tall picture', () => {
    expect(centredSquare(200, 500)).toEqual({ x: 0, y: 150, side: 200 })
  })

  it('keeps a square as it is', () => {
    expect(centredSquare(300, 300)).toEqual({ x: 0, y: 0, side: 300 })
  })
})

import { describe, expect, it } from 'vitest'
import { isSafeExternalUrl, resolveEmbedUrl } from './url.js'

describe('isSafeExternalUrl', () => {
  it('accepts absolute https links only', () => {
    expect(isSafeExternalUrl('https://jwt.io/introduction')).toBe(true)
    expect(isSafeExternalUrl('http://example.com')).toBe(false)
    expect(isSafeExternalUrl('javascript:alert(1)')).toBe(false)
    expect(isSafeExternalUrl('/relative/path')).toBe(false)
    expect(isSafeExternalUrl(undefined)).toBe(false)
  })
})

describe('resolveEmbedUrl', () => {
  it('resolves same-origin paths and https URLs', () => {
    expect(resolveEmbedUrl('/mock-learning-app/index.html?activityId=a1').href).toBe(
      `${window.location.origin}/mock-learning-app/index.html?activityId=a1`,
    )
    expect(resolveEmbedUrl('https://lab.example.com/play/1').origin).toBe('https://lab.example.com')
  })

  it('refuses addresses that are not safe to embed', () => {
    expect(resolveEmbedUrl('http://lab.example.com/play/1')).toBeNull()
    expect(resolveEmbedUrl('javascript:alert(1)')).toBeNull()
    expect(resolveEmbedUrl('data:text/html,<p>hi</p>')).toBeNull()
    expect(resolveEmbedUrl('http://[invalid')).toBeNull()
  })
})

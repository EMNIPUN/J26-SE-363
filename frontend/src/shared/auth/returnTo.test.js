import { beforeEach, describe, expect, it } from 'vitest'
import { rememberReturnTo, takeReturnTo } from './returnTo.js'

function stubSessionStorage() {
  const store = new Map()
  globalThis.sessionStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
  }
}

describe('returnTo', () => {
  beforeEach(stubSessionStorage)

  it('gives back the remembered page once', () => {
    rememberReturnTo('/invitations?token=abc')
    expect(takeReturnTo()).toBe('/invitations?token=abc')
    expect(takeReturnTo()).toBeNull()
  })

  it('never follows an address that leaves the app', () => {
    rememberReturnTo('https://evil.example/phish')
    expect(takeReturnTo()).toBeNull()
    rememberReturnTo('//evil.example')
    expect(takeReturnTo()).toBeNull()
  })

  it('does nothing when storage is unavailable', () => {
    delete globalThis.sessionStorage
    expect(() => rememberReturnTo('/home')).not.toThrow()
    expect(takeReturnTo()).toBeNull()
  })
})

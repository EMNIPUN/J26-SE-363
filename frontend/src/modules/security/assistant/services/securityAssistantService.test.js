import { afterEach, describe, expect, it, vi } from 'vitest'
import bundle from '../demo/demoBundle.json'
import { isDemoMode } from '../config.js'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

describe('demo mode', () => {
  it('is off unless it is switched on on purpose', () => {
    expect(isDemoMode({})).toBe(false)
    expect(isDemoMode({ VITE_SECURITY_ASSISTANT_DEMO: 'false' })).toBe(false)
    expect(isDemoMode({ VITE_SECURITY_ASSISTANT_DEMO: '' })).toBe(false)
    expect(isDemoMode({ VITE_SECURITY_ASSISTANT_DEMO: 'true' })).toBe(true)
    expect(isDemoMode({ VITE_SECURITY_ASSISTANT_DEMO: 'TRUE' })).toBe(true)
  })

  it('answers from the bundle, labelled as demo data, and does not call the API', async () => {
    vi.stubEnv('VITE_SECURITY_ASSISTANT_DEMO', 'true')
    const get = vi.fn()
    vi.doMock('@/shared/api/apiClient.js', () => ({ default: { get } }))
    const { securityAssistantService: service } = await import('./securityAssistantService.js')

    const runs = await service.runs('J26-SE-363')
    expect(runs.demo_data).toBe(true)
    expect(runs.runs.map((r) => r.run_id).sort()).toEqual(['sample-python-demo', 'sample-python-no-llm'])
    const overview = await service.run('J26-SE-363', 'sample-python-demo')
    expect(overview.demo_data).toBe(true)
    expect(await service.students('J26-SE-363')).toEqual(bundle.students)
    await expect(service.run('J26-SE-363', 'nope')).rejects.toMatchObject({ status: 404 })
    expect(get).not.toHaveBeenCalled()
  })

  it('returns copies, so a page cannot change the sample for the next one', async () => {
    vi.stubEnv('VITE_SECURITY_ASSISTANT_DEMO', 'true')
    vi.doMock('@/shared/api/apiClient.js', () => ({ default: { get: vi.fn() } }))
    const { securityAssistantService: service } = await import('./securityAssistantService.js')
    const first = await service.runs('x')
    first.runs.length = 0
    expect((await service.runs('x')).runs).toHaveLength(2)
  })

  it('calls the Core API when demo mode is off, and an error stays an error', async () => {
    const get = vi.fn().mockResolvedValue({ runs: [], demo_data: false })
    vi.doMock('@/shared/api/apiClient.js', () => ({ default: { get } }))
    const { securityAssistantService: service } = await import('./securityAssistantService.js')
    expect(await service.runs('J26-SE-363')).toEqual({ runs: [], demo_data: false })
    expect(get).toHaveBeenCalledWith('/security-assistant/teams/J26-SE-363/runs')
    await service.run('J26-SE-363', 'r1', { student: 'u1' })
    expect(get).toHaveBeenLastCalledWith('/security-assistant/teams/J26-SE-363/runs/r1', { params: { student: 'u1' } })
    get.mockRejectedValueOnce(new Error('network down'))
    await expect(service.students('J26-SE-363')).rejects.toThrow('network down') // no silent fallback to the sample
  })
})

describe('the stand-alone demo page', () => {
  it('switches demo mode on for itself, on purpose', async () => {
    vi.resetModules()
    const config = await import('../config.js')
    expect(config.isDemoMode({})).toBe(false)
    config.forceDemoMode()
    expect(config.isDemoMode({})).toBe(true)
  })
})

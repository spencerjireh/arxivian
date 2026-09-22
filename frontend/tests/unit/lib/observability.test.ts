const configureFrontend = vi.fn()
const sdkReportError = vi.fn()
vi.mock('@pydantic/logfire-browser', () => ({
  default: { configureFrontend, reportError: sdkReportError },
}))

async function load() {
  return import('@/lib/observability')
}

beforeEach(() => {
  vi.resetModules()
  configureFrontend.mockClear()
  sdkReportError.mockClear()
  vi.unstubAllEnvs()
})

describe('observability', () => {
  it('does nothing without a token: no SDK load, reportError is a no-op', async () => {
    vi.stubEnv('VITE_LOGFIRE_TOKEN', '')
    vi.stubEnv('VITE_LOGFIRE_BASE_URL', 'https://logfire-us.pydantic.dev')
    const mod = await load()
    await mod.configureObservability()
    mod.reportError(new Error('boom'))
    expect(configureFrontend).not.toHaveBeenCalled()
    expect(sdkReportError).not.toHaveBeenCalled()
  })

  it('configures the frontend SDK once with the token and stamps route and user on spans', async () => {
    vi.stubEnv('VITE_LOGFIRE_TOKEN', 'pylf_v1_us_frontend')
    vi.stubEnv('VITE_LOGFIRE_BASE_URL', 'https://logfire-us.pydantic.dev')
    const mod = await load()
    await mod.configureObservability()
    await mod.configureObservability()
    expect(configureFrontend).toHaveBeenCalledTimes(1)

    const options = configureFrontend.mock.calls[0][0] as {
      baseUrl: string
      token: string
      rum: { session: { getRouteName: () => string | undefined; getUser: () => unknown } }
    }
    expect(options.baseUrl).toBe('https://logfire-us.pydantic.dev')
    expect(options.token).toBe('pylf_v1_us_frontend')
    expect(options.rum.session.getRouteName()).toBeUndefined()
    expect(options.rum.session.getUser()).toBeUndefined()

    mod.setObservabilityContext({ route: '/papers/:arxivId', userId: 'u-1' })
    expect(options.rum.session.getRouteName()).toBe('/papers/:arxivId')
    expect(options.rum.session.getUser()).toEqual({ id: 'u-1' })
    mod.setObservabilityContext({ userId: null })
    expect(options.rum.session.getUser()).toBeUndefined()
  })

  it('forwards boundary errors to the SDK once configured', async () => {
    vi.stubEnv('VITE_LOGFIRE_TOKEN', 'pylf_v1_us_frontend')
    vi.stubEnv('VITE_LOGFIRE_BASE_URL', 'https://logfire-us.pydantic.dev')
    const mod = await load()
    const error = new Error('render failed')
    mod.reportError(error)
    expect(sdkReportError).not.toHaveBeenCalled()
    await mod.configureObservability()
    mod.reportError(error, { componentStack: 'at Foo' })
    expect(sdkReportError).toHaveBeenCalledWith('render failed', error, {
      componentStack: 'at Foo',
    })
    mod.reportError('plain string')
    expect(sdkReportError).toHaveBeenLastCalledWith('plain string', 'plain string', undefined)
  })
})

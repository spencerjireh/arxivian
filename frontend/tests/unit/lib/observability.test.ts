import type { TransportItem } from '@grafana/faro-web-sdk'

const pushError = vi.fn()
const setUser = vi.fn()
const setView = vi.fn()

interface FaroApi {
  pushError: typeof pushError
  setUser: typeof setUser
  setView: typeof setView
}
// Typed generic rather than a named parameter, matching tests/mocks/lifecycle.ts: it gives the
// call signature an argument so `mock.calls[0][0]` type-checks, with nothing unused to lint.
const initializeFaro = vi.fn<(options: unknown) => { api: FaroApi }>(() => ({
  api: { pushError, setUser, setView },
}))

vi.mock('@grafana/faro-web-sdk', () => ({
  initializeFaro,
  ErrorsInstrumentation: class ErrorsInstrumentation {},
  WebVitalsInstrumentation: class WebVitalsInstrumentation {},
}))

async function load() {
  return import('@/lib/observability')
}

/** The options `initializeFaro` was called with, typed for the assertions below. */
interface Options {
  url: string
  apiKey: string | undefined
  app: { name: string; environment: string }
  instrumentations: unknown[]
  sessionTracking: { enabled: boolean }
  user: { id: string } | undefined
  view: { name: string }
  beforeSend: (item: TransportItem) => TransportItem
}

function optionsOf(): Options {
  return initializeFaro.mock.calls[0][0] as Options
}

const URL = 'https://faro.example.com/collect'

beforeEach(() => {
  vi.resetModules()
  initializeFaro.mockClear()
  pushError.mockClear()
  setUser.mockClear()
  setView.mockClear()
  vi.unstubAllEnvs()
})

describe('observability', () => {
  it('does nothing without a url: no SDK load, every export is a no-op', async () => {
    vi.stubEnv('VITE_FARO_URL', '')
    vi.stubEnv('VITE_FARO_API_KEY', 'key')
    const mod = await load()
    await mod.configureObservability()
    mod.setObservabilityContext({ route: '/feed', userId: 'u-1' })
    mod.reportError(new Error('boom'))
    expect(initializeFaro).not.toHaveBeenCalled()
    expect(pushError).not.toHaveBeenCalled()
  })

  it('configures once, with a narrow instrumentation set and no session tracking', async () => {
    vi.stubEnv('VITE_FARO_URL', URL)
    vi.stubEnv('VITE_FARO_API_KEY', 'key')
    const mod = await load()
    await mod.configureObservability()
    await mod.configureObservability()
    expect(initializeFaro).toHaveBeenCalledTimes(1)

    const options = optionsOf()
    expect(options.url).toBe(URL)
    expect(options.apiKey).toBe('key')
    expect(options.app.name).toBe('arxivian-web')
    // Two instrumentations only: getWebInstrumentations() would add console, user-action,
    // performance, navigation, CSP and session capture.
    expect(options.instrumentations).toHaveLength(2)
    // Off, not merely non-persistent: the volatile manager still writes to sessionStorage.
    expect(options.sessionTracking).toEqual({ enabled: false })
  })

  it('omits the api key when it is empty rather than sending a blank header', async () => {
    vi.stubEnv('VITE_FARO_URL', URL)
    vi.stubEnv('VITE_FARO_API_KEY', '')
    const mod = await load()
    await mod.configureObservability()
    expect(optionsOf().apiKey).toBeUndefined()
  })

  it('replays context recorded before the lazy import resolved', async () => {
    vi.stubEnv('VITE_FARO_URL', URL)
    const mod = await load()
    mod.setObservabilityContext({ route: '/papers/:arxivId', userId: 'u-1' })
    await mod.configureObservability()

    const options = optionsOf()
    expect(options.view).toEqual({ name: '/papers/:arxivId' })
    expect(options.user).toEqual({ id: 'u-1' })
    // Nothing was pushed: the values arrived as the initial metas.
    expect(setView).not.toHaveBeenCalled()
  })

  it('pushes later context changes, and names an unmatched route', async () => {
    vi.stubEnv('VITE_FARO_URL', URL)
    const mod = await load()
    await mod.configureObservability()

    mod.setObservabilityContext({ route: '/library', userId: 'u-1' })
    expect(setView).toHaveBeenLastCalledWith({ name: '/library' })
    expect(setUser).toHaveBeenLastCalledWith({ id: 'u-1' })

    mod.setObservabilityContext({ userId: null })
    expect(setUser).toHaveBeenLastCalledWith(undefined)

    mod.setObservabilityContext({ route: undefined })
    expect(setView).toHaveBeenLastCalledWith({ name: 'unknown' })
  })

  it('forwards boundary errors once configured, coercing value and context', async () => {
    vi.stubEnv('VITE_FARO_URL', URL)
    const mod = await load()
    const error = new Error('render failed')
    mod.reportError(error)
    expect(pushError).not.toHaveBeenCalled()

    await mod.configureObservability()
    mod.reportError(error, { componentStack: 'at Foo' })
    expect(pushError).toHaveBeenCalledWith(error, { context: { componentStack: 'at Foo' } })

    // A non-Error is wrapped; pushError only accepts an Error.
    mod.reportError('plain string')
    const [value, options] = pushError.mock.calls[1] as [Error, { context?: unknown }]
    expect(value).toBeInstanceOf(Error)
    expect(value.message).toBe('plain string')
    expect(options.context).toBeUndefined()
  })

  it('drops nullish context values and truncates long ones', async () => {
    vi.stubEnv('VITE_FARO_URL', URL)
    const mod = await load()
    await mod.configureObservability()

    mod.reportError(new Error('e'), { componentStack: null, count: 3 })
    expect(pushError).toHaveBeenLastCalledWith(expect.any(Error), { context: { count: '3' } })

    mod.reportError(new Error('e'), { componentStack: 'x'.repeat(5000) })
    const [, options] = pushError.mock.calls[1] as [Error, { context: Record<string, string> }]
    expect(options.context.componentStack).toHaveLength(2000)
  })

  it('strips the query string so a conversation id never leaves the browser', async () => {
    vi.stubEnv('VITE_FARO_URL', URL)
    const mod = await load()
    await mod.configureObservability()

    const item = {
      meta: { page: { url: 'https://arxivian.test/papers/2609.1?session=abc#frag', id: 'p' } },
      payload: { kind: 'exception' },
    } as unknown as TransportItem
    const sent = optionsOf().beforeSend(item)

    expect(sent.meta.page?.url).toBe('https://arxivian.test/papers/2609.1')
    expect(sent.meta.page?.id).toBe('p')
    expect(sent.payload).toBe(item.payload)
  })

  it('leaves an item with no page meta alone', async () => {
    vi.stubEnv('VITE_FARO_URL', URL)
    const mod = await load()
    await mod.configureObservability()
    const item = { meta: {}, payload: {} } as unknown as TransportItem
    expect(optionsOf().beforeSend(item)).toBe(item)
  })
})

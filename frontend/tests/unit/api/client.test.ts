import { apiPut, apiPatch, apiDelete, ApiError } from '../../../src/api/client'

function mockFetch(status: number, body: unknown = null) {
  const response = {
    ok: status >= 200 && status < 300,
    status,
    statusText: 'x',
    json: vi.fn().mockResolvedValue(body),
    text: vi.fn().mockResolvedValue(JSON.stringify(body)),
  }
  const fetchMock = vi.fn().mockResolvedValue(response)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api client verbs', () => {
  it('apiPut sends a JSON body with PUT', async () => {
    const fetchMock = mockFetch(200, { state: 'saved' })
    const out = await apiPut<{ state: string }>('/papers/x/state', { state: 'saved' })
    expect(out).toEqual({ state: 'saved' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/papers/x/state')
    expect(init.method).toBe('PUT')
    expect(init.body).toBe(JSON.stringify({ state: 'saved' }))
    expect(init.headers['Content-Type']).toBe('application/json')
  })

  it('apiPatch sends PATCH', async () => {
    const fetchMock = mockFetch(200, { ok: true })
    await apiPatch('/users/me/preferences', { a: 1 })
    expect(fetchMock.mock.calls[0][1].method).toBe('PATCH')
  })

  it('a 204 resolves to undefined without parsing a body', async () => {
    const fetchMock = mockFetch(204)
    const out = await apiDelete('/papers/x/state')
    expect(out).toBeUndefined()
    const response = await fetchMock.mock.results[0].value
    expect(response.json).not.toHaveBeenCalled()
  })

  it('non-2xx throws ApiError with the detail message', async () => {
    mockFetch(404, { detail: 'Paper not found' })
    await expect(apiPut('/papers/x/state', { state: 'saved' })).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      message: 'Paper not found',
    })
    await expect(apiPut('/papers/x/state', { state: 'saved' })).rejects.toBeInstanceOf(ApiError)
  })
})

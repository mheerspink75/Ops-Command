import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  setAccessToken,
  getAccessToken,
  setRefreshToken,
  getRefreshToken,
  clearTokens,
  api,
  getIncidents,
  getWSUrl,
  login,
} from './client'

function mockResponse(status: number, body?: unknown): Response {
  const ok = status >= 200 && status < 300
  return {
    ok,
    status,
    statusText: 'status',
    json: async () => body,
  } as unknown as Response
}

describe('token management', () => {
  beforeEach(() => {
    localStorage.clear()
    setAccessToken(null)
    setRefreshToken(null)
  })

  it('stores and retrieves the access token', () => {
    setAccessToken('abc')
    expect(getAccessToken()).toBe('abc')
    expect(localStorage.getItem('oc_access_token')).toBe('abc')
  })

  it('stores and retrieves the refresh token', () => {
    setRefreshToken('def')
    expect(getRefreshToken()).toBe('def')
    expect(localStorage.getItem('oc_refresh_token')).toBe('def')
  })

  it('clears both tokens from memory and storage', () => {
    setAccessToken('abc')
    setRefreshToken('def')
    clearTokens()
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
    expect(localStorage.getItem('oc_access_token')).toBeNull()
    expect(localStorage.getItem('oc_refresh_token')).toBeNull()
  })
})

describe('request', () => {
  beforeEach(() => {
    localStorage.clear()
    setAccessToken(null)
    setRefreshToken(null)
    vi.stubGlobal('fetch', vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends the Authorization header when a token is present', async () => {
    setAccessToken('tok123')
    vi.mocked(fetch).mockResolvedValueOnce(mockResponse(200, { ok: true }))
    await api.get('/api/v1/thing')
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(url).toContain('/api/v1/thing')
    expect((init as RequestInit).headers).toMatchObject({ Authorization: 'Bearer tok123' })
  })

  it('throws an ApiError carrying backend error details on failure', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      mockResponse(400, { error: { code: 'bad_request', message: 'Nope' } }),
    )
    await expect(api.get('/api/v1/thing')).rejects.toMatchObject({
      status: 400,
      code: 'bad_request',
      message: 'Nope',
    })
  })

  it('returns undefined for a 204 response', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(mockResponse(204))
    const result = await api.delete('/api/v1/thing')
    expect(result).toBeUndefined()
  })

  it('refreshes on 401 and retries the request once', async () => {
    setAccessToken('expired')
    setRefreshToken('refresh123')
    vi.mocked(fetch)
      .mockResolvedValueOnce(mockResponse(401, { error: { code: 'unauthorized', message: 'expired' } }))
      .mockResolvedValueOnce(
        mockResponse(200, {
          access_token: 'new',
          refresh_token: 'newr',
          token_type: 'bearer',
          expires_in: 3600,
        }),
      )
      .mockResolvedValueOnce(mockResponse(200, { ok: true }))
    const result = await api.get('/api/v1/thing')
    expect(result).toEqual({ ok: true })
    expect(getAccessToken()).toBe('new')
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(3)
  })

  it('clears tokens and throws when the refresh also fails', async () => {
    setAccessToken('expired')
    setRefreshToken('badrefresh')
    vi.mocked(fetch)
      .mockResolvedValueOnce(mockResponse(401, { error: { code: 'unauthorized', message: 'expired' } }))
      .mockResolvedValueOnce(mockResponse(401, { error: { code: 'invalid', message: 'bad refresh' } }))
    await expect(api.get('/api/v1/thing')).rejects.toMatchObject({
      status: 401,
      code: 'unauthorized',
    })
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })
})

describe('login', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })
  afterEach(() => vi.unstubAllGlobals())

  it('posts credentials to the login endpoint', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      mockResponse(200, {
        access_token: 'a',
        refresh_token: 'r',
        token_type: 'bearer',
        expires_in: 3600,
      }),
    )
    const result = await login('e@x.com', 'pw')
    expect(result.access_token).toBe('a')
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(url).toContain('/api/v1/auth/login')
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({
      email: 'e@x.com',
      password: 'pw',
    })
  })
})

describe('getIncidents query string', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse(200, { items: [] })))
  })
  afterEach(() => vi.unstubAllGlobals())

  it('builds the query string from params', async () => {
    await getIncidents('org1', { status: 'active', severity: 'SEV1', q: 'foo', limit: 10, offset: 20 })
    const [url] = vi.mocked(fetch).mock.calls[0]
    expect(url).toContain('/api/v1/organizations/org1/incidents?')
    expect(url).toContain('status=active')
    expect(url).toContain('severity=SEV1')
    expect(url).toContain('q=foo')
    expect(url).toContain('limit=10')
    expect(url).toContain('offset=20')
  })

  it('omits the query string when no params are given', async () => {
    await getIncidents('org1')
    const [url] = vi.mocked(fetch).mock.calls[0]
    expect(url).toBe('http://localhost:8000/api/v1/organizations/org1/incidents')
  })
})

describe('getWSUrl', () => {
  it('includes the incident id and the access token', () => {
    setAccessToken('wstok')
    const url = getWSUrl('inc1')
    expect(url).toContain('/api/v1/ws/incidents/inc1')
    expect(url).toContain('token=wstok')
  })
})

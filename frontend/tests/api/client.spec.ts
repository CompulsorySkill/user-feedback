import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from '@/api/client'

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns undefined for 204 responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))

    await expect(api.delete('/v1/posts/1/vote')).resolves.toBeUndefined()
  })

  it('turns { detail, code } into ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse({ detail: '看板不存在', code: 'BOARD_NOT_FOUND' }, { status: 404 }),
        ),
    )

    await expect(api.get('/v1/boards/nope')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      code: 'BOARD_NOT_FOUND',
      message: '看板不存在',
    })
  })

  it('refreshes an expired session and replays the request once', async () => {
    const refreshed = vi.fn()
    window.addEventListener('feedlog:auth-refreshed', refreshed)
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(
          { detail: 'expired', code: 'UNAUTHENTICATED' },
          {
            status: 401,
            headers: { 'X-Session-Expired': '1' },
          },
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 200 }))
      .mockResolvedValueOnce(jsonResponse({ items: [] }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await api.get('/v1/posts')

    expect(result).toEqual({ items: [] })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(String(fetchMock.mock.calls[1][0])).toContain('/v1/auth/refresh')
    expect(refreshed).toHaveBeenCalledTimes(1)
    window.removeEventListener('feedlog:auth-refreshed', refreshed)
  })

  it('downgrades to anonymous when refresh fails', async () => {
    const expired = vi.fn()
    window.addEventListener('feedlog:auth-expired', expired)
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(
          { detail: 'expired', code: 'UNAUTHENTICATED' },
          {
            status: 401,
            headers: { 'X-Session-Expired': '1' },
          },
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(api.get('/v1/posts')).rejects.toBeInstanceOf(ApiError)
    expect(expired).toHaveBeenCalledTimes(1)
    window.removeEventListener('feedlog:auth-expired', expired)
  })
})

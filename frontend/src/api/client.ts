/** 统一 API 客户端：错误响应固定为 { detail, code }。
 *
 * 会话续期：
 * - 后端发现 access cookie 失效时会在响应头返回 `X-Session-Expired: 1`；
 * - 这里尝试一次 `/auth/refresh`（并发请求共享同一个 Promise），成功后重放原请求；
 * - 刷新失败则广播 `feedlog:auth-expired`，由 App 重新水合为匿名状态。
 */

const API_BASE = '/api'

export interface ApiErrorPayload {
  detail: unknown
  code: string
}

export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

let refreshPromise: Promise<boolean> | null = null

function refreshAccessToken(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/v1/auth/refresh`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
      .then((response) => response.ok)
      .catch(() => false)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload | null = null
  try {
    payload = (await response.json()) as ApiErrorPayload
  } catch {
    payload = null
  }

  const code = payload?.code ?? `HTTP_${response.status}`
  const detail = payload?.detail
  const message =
    typeof detail === 'string' && detail.length > 0 ? detail : `${code}（${response.status}）`
  return new ApiError(response.status, code, message)
}

async function request<T>(path: string, init: RequestInit = {}, retried = false): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  })

  const sessionExpired = response.headers.get('X-Session-Expired') === '1'
  if (!retried && sessionExpired && !path.startsWith('/v1/auth/refresh')) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      window.dispatchEvent(new Event('feedlog:auth-refreshed'))
      return request<T>(path, init, true)
    }
    window.dispatchEvent(new Event('feedlog:auth-expired'))
  }

  if (!response.ok) {
    throw await parseError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }
  const text = await response.text()
  return (text ? JSON.parse(text) : undefined) as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'POST',
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'PATCH',
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

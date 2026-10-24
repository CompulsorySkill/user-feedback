/** 统一 API 客户端：错误响应固定为 { detail, code }。 */

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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  })

  if (!response.ok) {
    throw await parseError(response)
  }

  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
}

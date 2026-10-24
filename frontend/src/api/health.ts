import { api } from './client'

export interface HealthResponse {
  status: 'ok'
  database: 'ok'
  name: string
  version: string
  environment: string
}

export function getHealth(): Promise<HealthResponse> {
  return api.get<HealthResponse>('/health')
}

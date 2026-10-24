import { api } from './client'
import type { UploadPurpose, UploadTicket } from './types'

export interface PresignInput {
  filename: string
  content_type: string
  purpose: UploadPurpose
  size: number
}

export function presignUpload(input: PresignInput): Promise<UploadTicket> {
  return api.post<UploadTicket>('/v1/uploads/presign', input)
}

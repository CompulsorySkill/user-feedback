import { ref } from 'vue'
import { ApiError } from '@/api/client'
import { presignUpload } from '@/api/uploads'
import type { UploadPurpose } from '@/api/types'

const MAX_BYTES = 104857600
const ALLOWED_CONTENT_TYPES = new Set([
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/gif',
  'video/mp4',
])

/** presign -> PUT 直传 RustFS，返回 object key。 */
export function useUpload() {
  const uploading = ref(false)
  const error = ref('')

  async function upload(file: File, purpose: UploadPurpose): Promise<string | null> {
    error.value = ''
    const isAttachment = purpose === 'changelog_attachment'

    if (!isAttachment && !ALLOWED_CONTENT_TYPES.has(file.type)) {
      error.value = '仅支持 PNG / JPEG / WebP / GIF 图片与 MP4 视频'
      return null
    }
    if (file.size > MAX_BYTES) {
      error.value = '单文件不能超过 100MB'
      return null
    }

    uploading.value = true
    try {
      const ticket = await presignUpload({
        filename: file.name,
        content_type: file.type || 'application/octet-stream',
        purpose,
        size: file.size,
      })
      const response = await fetch(ticket.upload_url, {
        method: ticket.method,
        headers: ticket.headers,
        body: file,
      })
      if (!response.ok) {
        throw new Error(`直传失败（HTTP ${response.status}）`)
      }
      return ticket.object_key
    } catch (err) {
      error.value =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : '上传失败，请重试'
      return null
    } finally {
      uploading.value = false
    }
  }

  return { uploading, error, upload }
}

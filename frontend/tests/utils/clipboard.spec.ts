import { describe, expect, it } from 'vitest'
import { imageFilesFromClipboard } from '@/utils/clipboard'

function clipboard(files: File[]) {
  return { files } as unknown as Pick<DataTransfer, 'files'>
}

describe('imageFilesFromClipboard', () => {
  it('returns only image files and ignores anything else', () => {
    const png = new File(['x'], 'screenshot.png', { type: 'image/png' })
    const txt = new File(['x'], 'note.txt', { type: 'text/plain' })

    expect(imageFilesFromClipboard(clipboard([png, txt]))).toEqual([png])
  })

  it('handles empty or missing clipboard data', () => {
    expect(imageFilesFromClipboard(null)).toEqual([])
    expect(imageFilesFromClipboard(clipboard([]))).toEqual([])
  })
})

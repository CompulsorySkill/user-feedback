import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const presignUpload = vi.hoisted(() => vi.fn());

vi.mock('@/api/uploads', () => ({ presignUpload }));

import { useUpload } from '@/composables/useUpload';

describe('useUpload', () => {
  beforeEach(() => {
    presignUpload.mockResolvedValue({
      object_key: 'uploads/archive.bin',
      upload_url: 'http://storage.test/uploads/archive.bin',
      method: 'PUT',
      expires_in: 600,
      headers: { 'Content-Type': 'application/zip' },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 200 })));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('allows any file type for changelog attachments', async () => {
    const file = new File(['zip'], 'release.zip', { type: 'application/zip' });
    const { upload, error } = useUpload();

    await expect(upload(file, 'changelog_attachment')).resolves.toBe('uploads/archive.bin');
    expect(presignUpload).toHaveBeenCalledWith(
      expect.objectContaining({
        filename: 'release.zip',
        content_type: 'application/zip',
        purpose: 'changelog_attachment',
      }),
    );
    expect(error.value).toBe('');
  });

  it('falls back to octet-stream when the browser has no MIME type', async () => {
    const file = new File(['data'], 'unknown-file');
    const { upload } = useUpload();

    await upload(file, 'changelog_attachment');

    expect(presignUpload).toHaveBeenCalledWith(
      expect.objectContaining({ content_type: 'application/octet-stream' }),
    );
  });

  it('still rejects non-media types for post uploads', async () => {
    const file = new File(['zip'], 'release.zip', { type: 'application/zip' });
    const { upload, error } = useUpload();

    await expect(upload(file, 'post_image')).resolves.toBeNull();
    expect(presignUpload).not.toHaveBeenCalled();
    expect(error.value).toContain('仅支持');
  });
});

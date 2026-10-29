import { describe, expect, it } from 'vitest';

import { setStoragePrefix, storageUrl } from '@/composables/useStorageUrl';

describe('storageUrl', () => {
  it('prepends the default prefix to object keys', () => {
    expect(storageUrl('uploads/a.png')).toBe('/storage/uploads/a.png');
    expect(storageUrl('/uploads/a.png')).toBe('/storage/uploads/a.png');
  });

  it('uses the prefix reported by the backend (S3_BUCKET)', () => {
    setStoragePrefix('/media');
    expect(storageUrl('uploads/a.png')).toBe('/media/uploads/a.png');

    setStoragePrefix('media/');
    expect(storageUrl('uploads/a.png')).toBe('/media/uploads/a.png');

    setStoragePrefix('/storage');
    expect(storageUrl('uploads/a.png')).toBe('/storage/uploads/a.png');
  });

  it('passes absolute and data URLs through', () => {
    expect(storageUrl('https://cdn.example.com/a.png')).toBe('https://cdn.example.com/a.png');
    expect(storageUrl('data:image/png;base64,AAAA')).toBe('data:image/png;base64,AAAA');
  });
});

import { describe, expect, it } from 'vitest';

import { confirmState, settleConfirm, useConfirm } from '@/composables/useConfirm';

const confirm = useConfirm();

describe('useConfirm', () => {
  it('确认后返回 true 并关闭弹窗', async () => {
    const answer = confirm({ title: '确认删除？', message: '不可恢复' });
    expect(confirmState.open).toBe(true);
    expect(confirmState.title).toBe('确认删除？');
    expect(confirmState.message).toBe('不可恢复');
    settleConfirm(true);
    await expect(answer).resolves.toBe(true);
    expect(confirmState.open).toBe(false);
  });

  it('取消后返回 false', async () => {
    const answer = confirm({ title: '确认删除？' });
    settleConfirm(false);
    await expect(answer).resolves.toBe(false);
  });

  it('前一个未答复就开新的，前一个按取消处理', async () => {
    const first = confirm({ title: 'A' });
    const second = confirm({ title: 'B' });
    await expect(first).resolves.toBe(false);
    expect(confirmState.title).toBe('B');
    settleConfirm(true);
    await expect(second).resolves.toBe(true);
  });
});

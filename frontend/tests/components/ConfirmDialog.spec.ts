import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';

import ConfirmDialog from '@/components/ConfirmDialog.vue';
import { useConfirm } from '@/composables/useConfirm';

const confirm = useConfirm();
let wrapper: ReturnType<typeof mount> | null = null;

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  document.body.innerHTML = '';
});

function clickButton(label: string): void {
  const target = [...document.querySelectorAll('button')].find(
    (btn) => btn.textContent?.trim() === label,
  );
  if (!target) throw new Error(`找不到按钮：${label}`);
  target.click();
}

describe('ConfirmDialog', () => {
  it('点确认后 resolve true 并收起弹窗', async () => {
    wrapper = mount(ConfirmDialog, { attachTo: document.body });
    const answer = confirm({ title: '确认删除？', message: '不可恢复' });
    await flushPromises();
    expect(document.body.textContent).toContain('确认删除？');
    clickButton('确认');
    await flushPromises();
    await expect(answer).resolves.toBe(true);
  });

  it('点取消后 resolve false', async () => {
    wrapper = mount(ConfirmDialog, { attachTo: document.body });
    const answer = confirm({ title: '确认删除？' });
    await flushPromises();
    clickButton('取消');
    await flushPromises();
    await expect(answer).resolves.toBe(false);
  });
});

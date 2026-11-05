import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MentionOption } from '@/editor/mention';
import { createPopup } from '@/editor/mention';

function setup(items: MentionOption[]) {
  const command = vi.fn();
  const mount = vi.fn((element: HTMLElement) => {
    document.body.append(element);
    return () => element.remove();
  });
  const popup = createPopup();
  popup.onStart({ items, command, mount });
  const element = document.querySelector<HTMLElement>('.mention-popup');
  const activeLabel = () => element?.querySelector('.mention-item.is-active')?.textContent?.trim();
  return { popup, command, mount, element, activeLabel };
}

describe('管理员提及浮层', () => {
  const items: MentionOption[] = [
    { id: '1', label: 'Alice' },
    { id: '2', label: 'Bob' },
  ];

  beforeEach(() => {
    document.body.replaceChildren();
  });

  it('渲染候选项并用挂载函数交给编辑器定位', () => {
    const { element, mount } = setup(items);

    expect(mount).toHaveBeenCalledWith(element);
    expect(element?.textContent).toContain('@Alice');
    expect(element?.textContent).toContain('@Bob');
  });

  it('上下键循环选中，回车提交选中项', () => {
    const { popup, command, activeLabel } = setup(items);

    expect(activeLabel()).toBe('@Alice');
    popup.onKeyDown({ event: new KeyboardEvent('keydown', { key: 'ArrowDown' }) });
    expect(activeLabel()).toBe('@Bob');
    popup.onKeyDown({ event: new KeyboardEvent('keydown', { key: 'ArrowDown' }) });
    expect(activeLabel()).toBe('@Alice');
    popup.onKeyDown({ event: new KeyboardEvent('keydown', { key: 'ArrowUp' }) });
    expect(activeLabel()).toBe('@Bob');

    expect(popup.onKeyDown({ event: new KeyboardEvent('keydown', { key: 'Enter' }) })).toBe(true);
    expect(command).toHaveBeenCalledWith(items[1]);
  });

  it('没有匹配项时提示并忽略回车', () => {
    const { popup, command, element } = setup([]);

    expect(element?.textContent).toContain('没有匹配的管理员');
    expect(popup.onKeyDown({ event: new KeyboardEvent('keydown', { key: 'Enter' }) })).toBe(false);
    expect(command).not.toHaveBeenCalled();
  });

  it('退出时关闭浮层', () => {
    const { popup, element } = setup(items);

    popup.onExit();

    expect(element?.isConnected).toBe(false);
  });
});

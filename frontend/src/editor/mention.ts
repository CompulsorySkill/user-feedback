import Mention from '@tiptap/extension-mention';

import { listAdminMentions } from '@/api/site';

const MAX_ITEMS = 6;

/** Mention 节点的 attrs 就是 { id, label }，这里直接用它，省一层类型转换。 */
export interface MentionOption {
  id: string;
  label: string;
}

let adminCache: Promise<MentionOption[]> | null = null;

function loadAdmins(): Promise<MentionOption[]> {
  adminCache ??= listAdminMentions()
    .then((admins) => admins.map((admin) => ({ id: String(admin.id), label: admin.name })))
    .catch(() => {
      adminCache = null;
      return [];
    });
  return adminCache;
}

/** 浮层不引第三方定位库：suggestion 插件的 mount() 已负责跟随光标。 */
export function createPopup() {
  let element: HTMLDivElement | null = null;
  let detach: (() => void) | null = null;
  let items: MentionOption[] = [];
  let active = 0;
  let select: ((item: MentionOption) => void) | null = null;

  function paint(): void {
    if (!element) return;
    if (items.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'mention-empty';
      empty.textContent = '没有匹配的管理员';
      element.replaceChildren(empty);
      return;
    }
    element.replaceChildren(
      ...items.map((item, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = index === active ? 'mention-item is-active' : 'mention-item';
        button.textContent = `@${item.label}`;
        // mousedown 抢在焦点丢失之前提交，避免编辑器先失焦。
        button.addEventListener('mousedown', (event) => {
          event.preventDefault();
          select?.(item);
        });
        return button;
      }),
    );
  }

  function move(step: number): void {
    if (items.length === 0) return;
    active = (active + step + items.length) % items.length;
    paint();
  }

  return {
    onStart: (props: {
      items: MentionOption[];
      command: (item: MentionOption) => void;
      mount: (el: HTMLElement) => () => void;
    }) => {
      items = props.items;
      active = 0;
      select = props.command;
      element = document.createElement('div');
      element.className = 'mention-popup';
      paint();
      detach = props.mount(element);
    },
    onUpdate: (props: { items: MentionOption[]; command: (item: MentionOption) => void }) => {
      items = props.items;
      active = 0;
      select = props.command;
      paint();
    },
    onExit: () => {
      detach?.();
      detach = null;
      element = null;
      items = [];
    },
    onKeyDown: (props: { event: KeyboardEvent }): boolean => {
      const { key } = props.event;
      if (key === 'ArrowDown' || key === 'ArrowUp') {
        move(key === 'ArrowDown' ? 1 : -1);
        return true;
      }
      if (key === 'Enter' && items[active]) {
        select?.(items[active]);
        return true;
      }
      return false;
    },
  };
}

export const AdminMention = Mention.configure({
  HTMLAttributes: { class: 'rt-mention' },
  suggestion: {
    char: '@',
    items: async ({ query }) => {
      const admins = await loadAdmins();
      const keyword = query.trim().toLowerCase();
      return (
        keyword ? admins.filter((admin) => admin.label.toLowerCase().includes(keyword)) : admins
      ).slice(0, MAX_ITEMS);
    },
    command: ({ editor, range, props }) => {
      editor
        .chain()
        .focus()
        .insertContentAt(range, [
          { type: 'mention', attrs: { id: props.id, label: props.label } },
          { type: 'text', text: ' ' },
        ])
        .run();
    },
    render: createPopup,
  },
});

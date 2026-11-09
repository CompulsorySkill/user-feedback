import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { AdminTaskItem, Board } from '@/api/types';
import { Select } from '@/components/ui/select';

const mocks = vi.hoisted(() => ({
  listAdminTasks: vi.fn(),
  listBoards: vi.fn(),
}));

vi.mock('@/api/adminTasks', () => ({ listAdminTasks: mocks.listAdminTasks }));
vi.mock('@/api/boards', () => ({ listBoards: mocks.listBoards }));

import AdminTasksView from '@/views/AdminTasksView.vue';

// RouterLink 在测试里换成同构 <a>，用 data-to 定位链接
const RouterLinkStub = { props: ['to'], template: '<a :data-to="to"><slot /></a>' };

function board(overrides: Partial<Board> = {}): Board {
  return {
    id: 1,
    slug: 'product',
    name: '功能需求',
    description: null,
    is_public: true,
    allow_guest_posting: true,
    allow_guest_voting: true,
    allow_guest_commenting: true,
    post_count: 3,
    created_at: '2026-03-01T12:00:00Z',
    ...overrides,
  };
}

function task(overrides: Partial<AdminTaskItem> = {}): AdminTaskItem {
  return {
    post_id: 'post-1',
    title: '导出功能坏了',
    board_slug: 'product',
    board_name: '功能需求',
    status: 'open',
    mentioned_at: '2026-03-01T12:00:00Z',
    task_state: 'pending',
    assignee_name: null,
    accepted_at: null,
    completed_at: null,
    ...overrides,
  };
}

describe('AdminTasksView 任务面板', () => {
  beforeEach(() => {
    mocks.listAdminTasks.mockReset();
    mocks.listBoards.mockReset();
    mocks.listBoards.mockResolvedValue([board()]);
    document.body.innerHTML = '';
  });

  it('首屏列出被 @ 的反馈与任务状态，并链接到详情', async () => {
    mocks.listAdminTasks.mockResolvedValue({ items: [task()], next_cursor: null });
    const wrapper = mount(AdminTasksView, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    await flushPromises();

    expect(mocks.listAdminTasks).toHaveBeenCalledWith(
      expect.objectContaining({ limit: 30, taskState: null, board: null }),
    );
    expect(wrapper.text()).toContain('导出功能坏了');
    expect(wrapper.text()).toContain('功能需求');
    expect(wrapper.text()).toContain('待接受');
    expect(wrapper.text()).toContain('无人接受');
    expect(wrapper.find('a[data-to="/post/post-1"]').exists()).toBe(true);
  });

  it('已完成的任务显示接受人', async () => {
    mocks.listAdminTasks.mockResolvedValue({
      items: [
        task({
          task_state: 'done',
          assignee_name: 'Alice',
          accepted_at: '2026-03-02T12:00:00Z',
          completed_at: '2026-03-03T12:00:00Z',
        }),
      ],
      next_cursor: null,
    });
    const wrapper = mount(AdminTasksView);
    await flushPromises();

    expect(wrapper.text()).toContain('已完成');
    expect(wrapper.text()).toContain('Alice');
  });

  it('切换任务状态筛选时丢弃旧游标并重新加载', async () => {
    mocks.listAdminTasks
      .mockResolvedValueOnce({ items: [task()], next_cursor: 'cursor-1' })
      .mockResolvedValue({ items: [], next_cursor: null });
    const wrapper = mount(AdminTasksView);
    await flushPromises();

    wrapper.findAllComponents(Select)[0]!.vm.$emit('update:model-value', 'done');
    await flushPromises();

    const lastCall = mocks.listAdminTasks.mock.calls.at(-1)?.[0];
    expect(lastCall).toMatchObject({ taskState: 'done' });
    expect(lastCall).not.toHaveProperty('before');
    expect(wrapper.text()).toContain('还没有人 @ 你');
  });

  it('按看板筛选时带上 board 参数', async () => {
    mocks.listAdminTasks.mockResolvedValue({ items: [], next_cursor: null });
    const wrapper = mount(AdminTasksView);
    await flushPromises();

    wrapper.findAllComponents(Select)[1]!.vm.$emit('update:model-value', 'product');
    await flushPromises();

    expect(mocks.listAdminTasks.mock.calls.at(-1)?.[0]).toMatchObject({ board: 'product' });
  });
});

import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { AdminUserItem } from '@/api/types';

const mocks = vi.hoisted(() => ({
  listAdminUsers: vi.fn(),
}));

vi.mock('@/api/users', () => ({ listAdminUsers: mocks.listAdminUsers }));

import AdminUsersView from '@/views/AdminUsersView.vue';

function user(overrides: Partial<AdminUserItem> = {}): AdminUserItem {
  return {
    id: 1,
    email: 'alice@example.com',
    display_name: 'Alice',
    role: 'user',
    sso_provider: 'sso',
    post_count: 2,
    comment_count: 1,
    created_at: '2026-03-01T12:00:00Z',
    ...overrides,
  };
}

describe('AdminUsersView 用户目录', () => {
  beforeEach(() => {
    mocks.listAdminUsers.mockReset();
  });

  it('首屏加载用户并显示反馈 / 评论计数', async () => {
    mocks.listAdminUsers.mockResolvedValue({ items: [user({ role: 'admin' })], next_cursor: null });
    const wrapper = mount(AdminUsersView);
    await flushPromises();

    expect(mocks.listAdminUsers).toHaveBeenCalledWith(
      expect.objectContaining({ limit: 30, q: null, role: null }),
    );
    expect(wrapper.text()).toContain('alice@example.com');
    expect(wrapper.text()).toContain('2 反馈 · 1 评论');
    expect(wrapper.text()).toContain('ADMIN');
  });

  it('搜索时丢弃旧游标并从第一页重新加载', async () => {
    mocks.listAdminUsers
      .mockResolvedValueOnce({ items: [user()], next_cursor: '1' })
      .mockResolvedValue({ items: [user({ id: 9, email: 'bob@example.com' })], next_cursor: null });
    const wrapper = mount(AdminUsersView);
    await flushPromises();

    await wrapper.find('input[type="search"]').setValue('bob');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    const lastCall = mocks.listAdminUsers.mock.calls.at(-1)?.[0];
    expect(lastCall).toMatchObject({ q: 'bob' });
    expect(lastCall).not.toHaveProperty('before_id');
    expect(wrapper.text()).toContain('bob@example.com');
    expect(wrapper.text()).not.toContain('alice@example.com');
  });

  it('加载更多带上游标并去重', async () => {
    mocks.listAdminUsers
      .mockResolvedValueOnce({ items: [user()], next_cursor: '1' })
      .mockResolvedValueOnce({
        items: [user(), user({ id: 2, email: 'bob@example.com' })],
        next_cursor: null,
      });
    const wrapper = mount(AdminUsersView);
    await flushPromises();

    await wrapper.find('.load-more button').trigger('click');
    await flushPromises();

    expect(mocks.listAdminUsers.mock.calls.at(-1)?.[0]).toMatchObject({ before_id: 1 });
    expect(wrapper.findAll('.admin-item')).toHaveLength(2);
  });
});

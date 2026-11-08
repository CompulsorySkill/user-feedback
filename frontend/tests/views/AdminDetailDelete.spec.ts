import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { AnnouncementDetail, ChangelogDetail } from '@/api/types';

const mocks = vi.hoisted(() => ({
  params: { id: 'entry-1' },
  push: vi.fn(),
  getChangelog: vi.fn(),
  deleteChangelog: vi.fn(),
  getAnnouncement: vi.fn(),
  deleteAnnouncement: vi.fn(),
  publish: vi.fn(),
  unpublish: vi.fn(),
  pin: vi.fn(),
  unpin: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: mocks.params }),
  useRouter: () => ({ push: mocks.push }),
  RouterLink: { props: ['to'], template: '<a :data-to="to"><slot /></a>' },
}));
vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => async () => true,
}));
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ me: { id: 1 }, isAdmin: true, hydrate: async () => {} }),
}));
vi.mock('@/api/changelogs', () => ({
  getChangelog: mocks.getChangelog,
  deleteChangelog: mocks.deleteChangelog,
  publishChangelog: mocks.publish,
  unpublishChangelog: mocks.unpublish,
}));
vi.mock('@/api/announcements', () => ({
  getAnnouncement: mocks.getAnnouncement,
  deleteAnnouncement: mocks.deleteAnnouncement,
  publishAnnouncement: mocks.publish,
  unpublishAnnouncement: mocks.unpublish,
  pinAnnouncement: mocks.pin,
  unpinAnnouncement: mocks.unpin,
}));

import AnnouncementDetailView from '@/views/AnnouncementDetailView.vue';
import ChangelogDetailView from '@/views/ChangelogDetailView.vue';

const stamp = '2026-03-01T12:00:00Z';
const content = { type: 'doc', content: [] };

function changelog(): ChangelogDetail {
  return {
    id: 'entry-1',
    title: '已撤回的更新日志',
    excerpt: '',
    is_published: false,
    published_at: stamp,
    created_at: stamp,
    updated_at: stamp,
    content,
    attachments: [],
  };
}

function announcement(): AnnouncementDetail {
  return {
    id: 'entry-1',
    title: '已撤回的公告',
    excerpt: '',
    is_published: false,
    is_pinned: false,
    published_at: stamp,
    author_name: '管理员',
    created_at: stamp,
    updated_at: stamp,
    content,
    attachments: [],
  };
}

function findDeleteButton(wrapper: VueWrapper) {
  return wrapper.findAll('button').find((button) => button.text().includes('删除'));
}

describe('撤回发布的条目支持管理员删除', () => {
  beforeEach(() => {
    mocks.getChangelog.mockReset().mockResolvedValue(changelog());
    mocks.deleteChangelog.mockReset().mockResolvedValue(undefined);
    mocks.getAnnouncement.mockReset().mockResolvedValue(announcement());
    mocks.deleteAnnouncement.mockReset().mockResolvedValue(undefined);
    mocks.push.mockReset();
  });

  it('更新日志详情可删除并回到列表', async () => {
    const wrapper = mount(ChangelogDetailView);
    await flushPromises();

    expect(wrapper.text()).toContain('草稿（仅管理员可见）');
    const button = findDeleteButton(wrapper);
    expect(button).toBeTruthy();

    await button?.trigger('click');
    await flushPromises();

    expect(mocks.deleteChangelog).toHaveBeenCalledWith('entry-1');
    expect(mocks.push).toHaveBeenCalledWith('/changelog');
  });

  it('公告详情可删除并回到列表', async () => {
    const wrapper = mount(AnnouncementDetailView);
    await flushPromises();

    expect(wrapper.text()).toContain('草稿（仅管理员可见）');
    const button = findDeleteButton(wrapper);
    expect(button).toBeTruthy();

    await button?.trigger('click');
    await flushPromises();

    expect(mocks.deleteAnnouncement).toHaveBeenCalledWith('entry-1');
    expect(mocks.push).toHaveBeenCalledWith('/announcements');
  });
});

import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { PostDetail } from '@/api/types';

const mocks = vi.hoisted(() => ({
  accept: vi.fn(),
  complete: vi.fn(),
}));

vi.mock('@/api/postActions', () => ({
  acceptPostTask: mocks.accept,
  completePostTask: mocks.complete,
}));

import PostTimeline from '@/components/PostTimeline.vue';

const stamp = '2026-05-01T12:00:00Z';

function post(overrides: Partial<PostDetail> = {}): PostDetail {
  return {
    id: 'post-1',
    board_slug: 'general',
    board_name: 'General',
    title: '带时间线的反馈',
    excerpt: '',
    status: 'planned',
    vote_count: 0,
    comment_count: 0,
    author_name: 'Alice',
    anonymous_name: null,
    is_anonymous: false,
    created_at: stamp,
    updated_at: stamp,
    tags: [],
    board: { id: 1, slug: 'general', name: 'General' },
    content: { type: 'doc', content: [] },
    environment: null,
    is_author: false,
    timeline: [
      {
        id: 1,
        event_type: 'created',
        from_status: null,
        to_status: 'open',
        actor_name: 'Alice',
        created_at: stamp,
      },
      {
        id: 2,
        event_type: 'status_changed',
        from_status: 'open',
        to_status: 'planned',
        actor_name: 'Admin',
        created_at: stamp,
      },
    ],
    task: null,
    can_accept_task: true,
    can_complete_task: false,
    previous: [],
    next: [],
    references: [],
    ...overrides,
  };
}

describe('PostTimeline', () => {
  beforeEach(() => {
    mocks.accept.mockReset();
    mocks.complete.mockReset();
  });

  it('展示状态事件与修改人', () => {
    const wrapper = mount(PostTimeline, { props: { post: post() } });

    expect(wrapper.text()).toContain('提出反馈');
    expect(wrapper.text()).toContain('已计划');
    expect(wrapper.text()).toContain('Alice 提出');
    expect(wrapper.text()).toContain('Admin 修改状态');
  });

  it('被提及用户可接受任务并回传更新后的反馈', async () => {
    const updated = post({ status: 'in_progress', can_accept_task: false });
    mocks.accept.mockResolvedValue(updated);
    const wrapper = mount(PostTimeline, { props: { post: post() } });

    const button = wrapper.findAll('button').find((item) => item.text().includes('接受任务'));
    expect(button).toBeTruthy();
    await button?.trigger('click');
    await flushPromises();

    expect(mocks.accept).toHaveBeenCalledWith('post-1');
    expect(wrapper.emitted('updated')?.[0]).toEqual([updated]);
  });

  it('任务接受者可完成任务', async () => {
    const updated = post({ status: 'completed', can_accept_task: false, can_complete_task: false });
    mocks.complete.mockResolvedValue(updated);
    const wrapper = mount(PostTimeline, {
      props: {
        post: post({
          status: 'in_progress',
          task: {
            assignee_id: 2,
            assignee_name: 'Worker',
            accepted_at: stamp,
            completed_at: null,
          },
          can_accept_task: false,
          can_complete_task: true,
        }),
      },
    });

    expect(wrapper.text()).toContain('任务接受人：Worker');
    const button = wrapper.findAll('button').find((item) => item.text().includes('完成任务'));
    await button?.trigger('click');
    await flushPromises();

    expect(mocks.complete).toHaveBeenCalledWith('post-1');
    expect(wrapper.emitted('updated')?.[0]).toEqual([updated]);
  });
});

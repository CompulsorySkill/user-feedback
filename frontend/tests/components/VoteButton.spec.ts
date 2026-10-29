import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  votePost: vi.fn(),
  unvotePost: vi.fn(),
}))

vi.mock('@/api/posts', () => ({
  votePost: mocks.votePost,
  unvotePost: mocks.unvotePost,
}))

import VoteButton from '@/components/VoteButton.vue'

const KEY = 'feedback:voted-posts'

function mountButton(postId: string, initialCount = 1) {
  return mount(VoteButton, { props: { postId, initialCount } })
}

function storedIds(): string[] | null {
  return JSON.parse(localStorage.getItem(KEY) ?? 'null')
}

describe('VoteButton 已投票记录', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('投票后写入 localStorage，重新挂载时恢复', async () => {
    mocks.votePost.mockResolvedValue({ voted: true, vote_count: 3 })

    const wrapper = mountButton('post-1', 2)
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(storedIds()).toEqual(['post-1'])

    const restored = mountButton('post-1', 3)
    const other = mountButton('post-2')

    expect(restored.find('button').attributes('aria-pressed')).toBe('true')
    expect(other.find('button').attributes('aria-pressed')).toBe('false')

    wrapper.unmount()
    restored.unmount()
    other.unmount()
  })

  it('取消投票后从记录中移除，其他帖子保留', async () => {
    localStorage.setItem(KEY, JSON.stringify(['post-1', 'post-9']))
    mocks.unvotePost.mockResolvedValue({ voted: false, vote_count: 1 })

    const wrapper = mountButton('post-1', 2)
    expect(wrapper.find('button').attributes('aria-pressed')).toBe('true')

    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(storedIds()).toEqual(['post-9'])
    wrapper.unmount()
  })

  it('存储值被改坏时按未投票处理', () => {
    localStorage.setItem(KEY, '{"post-1":true}')

    const wrapper = mountButton('post-1')

    expect(wrapper.find('button').attributes('aria-pressed')).toBe('false')
    wrapper.unmount()
  })
})

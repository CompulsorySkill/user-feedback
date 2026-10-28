import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import CommentNode from '@/components/CommentNode.vue'
import type { CommentNodeData } from '@/types/comment'

const node: CommentNodeData = {
  id: 'comment-1',
  post_id: 'post-1',
  parent_id: null,
  content: '一条评论',
  author_name: 'alice',
  is_anonymous: false,
  created_at: '2026-03-01T12:00:00Z',
  children: [],
}

describe('CommentNode', () => {
  it('shows the exact timestamp as a tooltip', () => {
    const wrapper = mount(CommentNode, { props: { node, depth: 1 } })
    expect(wrapper.find('.comment-time').attributes('title')).toContain('2026')
  })

  it('hides the delete action unless canDelete is set', () => {
    const wrapper = mount(CommentNode, { props: { node, depth: 1 } })
    expect(wrapper.find('.comment-action-danger').exists()).toBe(false)
  })

  it('emits delete with the node when the admin clicks it', async () => {
    const wrapper = mount(CommentNode, {
      props: { node, depth: 1, canDelete: true },
    })

    await wrapper.find('.comment-action-danger').trigger('click')

    expect(wrapper.emitted('delete')?.[0]).toEqual([node])
  })
})

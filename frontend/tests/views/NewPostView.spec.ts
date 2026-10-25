import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import type { Board } from '@/api/types'

const mocks = vi.hoisted(() => ({
  params: {} as Record<string, string>,
  listBoards: vi.fn(),
  createPost: vi.fn(),
  listBuiltinTags: vi.fn(),
  replace: vi.fn(),
  push: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: mocks.params }),
  useRouter: () => ({ replace: mocks.replace, push: mocks.push }),
  RouterLink: { props: ['to'], template: '<a :data-to="to"><slot /></a>' },
}))
vi.mock('@/api/boards', () => ({
  listBoards: mocks.listBoards,
  createPost: mocks.createPost,
}))
vi.mock('@/api/tags', () => ({ listBuiltinTags: mocks.listBuiltinTags }))
vi.mock('@/components/PostEditor.vue', () => ({
  default: {
    template: '<div class="editor-stub" />',
    methods: {
      getJSON: () => ({ type: 'doc', content: [] }),
      isEmpty: () => false,
    },
  },
}))

import NewPostView from '@/views/NewPostView.vue'

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
  }
}

function mountView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(NewPostView, { global: { plugins: [pinia] } })
}

describe('NewPostView 看板选择', () => {
  beforeEach(() => {
    mocks.params = {}
    mocks.listBoards.mockResolvedValue([
      board(),
      board({ id: 2, slug: 'bugs', name: '问题反馈' }),
      board({ id: 3, slug: 'internal', name: '内部看板', allow_guest_posting: false }),
    ])
    mocks.listBuiltinTags.mockResolvedValue([])
    mocks.createPost.mockResolvedValue({ id: 'post-1' })
  })

  it('从 /new 进入时默认第一个可匿名发布的看板，隐藏需登录的看板', async () => {
    const wrapper = mountView()
    await flushPromises()

    const select = wrapper.find('select')
    expect((select.element as HTMLSelectElement).value).toBe('product')
    expect(select.findAll('option').map((item) => item.attributes('value'))).toEqual([
      'product',
      'bugs',
    ])
    wrapper.unmount()
  })

  it('切换看板后表单与 URL 一起更新', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('select').setValue('bugs')
    await flushPromises()

    expect(mocks.replace).toHaveBeenCalledWith({
      name: 'new-post-board',
      params: { slug: 'bugs' },
    })
    expect(wrapper.find('.back-link').text()).toContain('问题反馈')
    wrapper.unmount()
  })

  it('提交时发布到所选的看板', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('select').setValue('bugs')
    await wrapper.find('input[maxlength="200"]').setValue('希望支持导出')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(mocks.createPost).toHaveBeenCalledWith('bugs', expect.objectContaining({}))
    expect(mocks.push).toHaveBeenCalledWith('/post/post-1')
    wrapper.unmount()
  })

  it('进入需登录的看板时保留选择并禁用发布', async () => {
    mocks.params = { slug: 'internal' }
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.notice-closed').exists()).toBe(true)
    expect(
      wrapper
        .find('select')
        .findAll('option')
        .map((item) => item.attributes('value')),
    ).toEqual(['product', 'bugs', 'internal'])
    expect(
      wrapper.find('.compose-buttons button[type="submit"]').attributes('disabled'),
    ).toBeDefined()
    wrapper.unmount()
  })
})

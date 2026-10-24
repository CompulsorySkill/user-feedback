import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TagPicker from '@/components/TagPicker.vue'
import type { TagSummary } from '@/api/types'

const suggestions: TagSummary[] = [
  { id: 1, name: '性能', is_builtin: true, post_count: 3 },
  { id: 2, name: '体验', is_builtin: true, post_count: 1 },
]

describe('TagPicker', () => {
  it('adds a suggested tag through v-model', async () => {
    const wrapper = mount(TagPicker, {
      props: { modelValue: [], suggestions },
    })

    await wrapper.find('.tag-suggestion').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([['性能']])
  })

  it('adds a custom tag on Enter and ignores duplicates', async () => {
    const wrapper = mount(TagPicker, {
      props: { modelValue: ['性能'], suggestions },
    })
    const input = wrapper.find('input')

    await input.setValue('  自定义  ')
    await input.trigger('keydown', { key: 'Enter' })

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([['性能', '自定义']])

    await input.setValue('性能')
    await input.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('update:modelValue')).toHaveLength(1)
  })

  it('disables input when the tag limit is reached', () => {
    const wrapper = mount(TagPicker, {
      props: { modelValue: ['a', 'b', 'c', 'd', 'e'], suggestions },
    })

    expect(wrapper.find('input').attributes('disabled')).toBeDefined()
    expect(wrapper.find('input').attributes('placeholder')).toContain('上限')
  })
})

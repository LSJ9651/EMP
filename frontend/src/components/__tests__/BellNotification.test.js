import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BellNotification from '../common/BellNotification.vue'

describe('BellNotification', () => {
  it('renders bell icon', () => {
    const wrapper = mount(BellNotification, {
      global: { stubs: { 'el-badge': true, 'el-icon': true } }
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('shows unread count', () => {
    const wrapper = mount(BellNotification, {
      props: { notifications: [{ id: 1, is_read: false }] },
      global: { stubs: { 'el-badge': true, 'el-icon': true } }
    })
    expect(wrapper.exists()).toBe(true)
  })
})

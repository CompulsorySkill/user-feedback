import { afterEach, describe, expect, it } from 'vitest'
import { appBase } from '@/config/base'

describe('appBase', () => {
  afterEach(() => {
    delete window.__FEEDLOG_BASE__
  })

  it('默认是根路径', () => {
    expect(appBase()).toBe('')
  })

  it('读取启动脚本注入的前缀并去掉尾斜杠', () => {
    window.__FEEDLOG_BASE__ = '/feedback'
    expect(appBase()).toBe('/feedback')

    window.__FEEDLOG_BASE__ = '/feedback/'
    expect(appBase()).toBe('/feedback')
  })
})

/**
 * 管理入口 / 筛选排序 / 编辑入口 冒烟测试。
 *
 *   pnpm smoke:admin
 *
 * 依赖本地 backend + vite 与 development 环境的 dev-login。
 */
import fs from 'node:fs'
import path from 'node:path'
import puppeteer from 'puppeteer-core'

const EDGE_PATH =
  process.env.EDGE_PATH ??
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const ADMIN_EMAIL = process.env.ADMIN_EMAIL ?? 'admin@example.com'
const CDP_URL = process.env.CDP_URL

const log = (message) => console.log(`[smoke-admin] ${message}`)

const browser = CDP_URL
  ? await puppeteer.connect({ browserURL: CDP_URL })
  : await puppeteer.launch({
      executablePath: EDGE_PATH,
      headless: true,
      pipe: false,
      args: [
        '--headless=new',
        '--no-first-run',
        '--disable-gpu',
        `--user-data-dir=${fs.mkdtempSync(path.join(process.env.TEMP ?? '/tmp', 'feedlog-admin-'))}`,
      ],
    })

try {
  const page = await browser.newPage()
  await page.setViewport({ width: 1280, height: 1000 })
  page.on('console', (message) => {
    if (message.type() === 'error') console.log(`[browser] ${message.text()}`)
  })

  // 1. 登录页 + 开发快速登录
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle2' })
  await page.waitForSelector('.login-grid')
  const emailInput = await page.$('input[type=email]')
  if (!emailInput) throw new Error('登录页缺少邮箱输入')
  await emailInput.evaluate((element, value) => {
    const input = element
    input.value = value
    input.dispatchEvent(new Event('input', { bubbles: true }))
  }, ADMIN_EMAIL)
  for (const button of await page.$$('button')) {
    const text = await button.evaluate((element) => element.textContent ?? '')
    if (text.includes('快速登录')) {
      await button.click()
      break
    }
  }
  await new Promise((resolve) => setTimeout(resolve, 500))
  await page.waitForSelector('.admin-badge', { timeout: 15000 })
  log('开发快速登录成功，头部显示管理员')

  // 2. 状态筛选
  await page.goto(`${BASE_URL}/b/product`, { waitUntil: 'networkidle2' })
  await page.waitForSelector('.filter-chip')
  for (const chip of await page.$$('.filter-chip')) {
    const text = await chip.evaluate((element) => element.textContent ?? '')
    if (text.trim() === '已关闭') {
      await chip.click()
      break
    }
  }
  await page.waitForFunction(() => location.search.includes('status=closed'))
  await page.waitForFunction(() => {
    const badges = [...document.querySelectorAll('.post-card .status-badge')]
    return badges.length > 0 && badges.every((node) => node.textContent?.includes('已关闭'))
  })
  log('状态筛选「已关闭」生效')

  // 3. 最热排序
  for (const button of await page.$$('.sort-button')) {
    const text = await button.evaluate((element) => element.textContent ?? '')
    if (text.trim() === '最热') {
      await button.click()
      break
    }
  }
  await page.waitForFunction(() => location.search.includes('sort=top'))
  await page.waitForFunction(() => document.querySelectorAll('.post-card').length > 0)
  const votes = await page.$$eval('.post-card .vote-count', (nodes) =>
    nodes.map((node) => Number(node.textContent)),
  )
  for (let index = 1; index < votes.length; index += 1) {
    if (votes[index] > votes[index - 1]) {
      throw new Error(`最热排序不是降序: ${votes.join(',')}`)
    }
  }
  log(`最热排序生效: ${votes.join(' ≥ ')}`)

  // 4. 管理员编辑已关闭反馈
  await page.click('.post-title-link')
  await page.waitForSelector('.post-detail-actions')
  const editLink = await page.$('.post-detail-actions a')
  if (!editLink) throw new Error('缺少编辑入口')
  await editLink.click()
  await page.waitForSelector('.tiptap')
  const titleInput = await page.$('.field-input')
  if (!titleInput) throw new Error('编辑页缺少标题输入')
  const newTitle = `管理员编辑 ${Date.now()}`
  await titleInput.evaluate((element, value) => {
    const input = element
    input.value = value
    input.dispatchEvent(new Event('input', { bubbles: true }))
  }, newTitle)
  for (const button of await page.$$('button')) {
    const text = await button.evaluate((element) => element.textContent ?? '')
    if (text.includes('保存修改')) {
      await button.click()
      break
    }
  }
  await page.waitForFunction(() => /\/post\/[0-9a-f-]+$/.test(location.pathname))
  await page.waitForFunction(
    (title) => document.querySelector('.post-detail h1')?.textContent?.trim() === title,
    { timeout: 10000 },
    newTitle,
  )
  log('管理员编辑已关闭反馈成功（标题已更新）')

  console.log('\n管理入口 / 筛选排序 / 编辑 冒烟测试通过')
} finally {
  await browser.close()
}

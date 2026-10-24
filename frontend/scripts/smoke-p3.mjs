/**
 * P3 浏览器冒烟测试：SSO 登录 → 状态流转 → 评论/回复 → 更新日志发布。
 *
 *   pnpm smoke:p3
 *
 * 需要 backend / vite 已启动；可用 CDP_URL 复用已开启调试端口的 Edge。
 */
import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import puppeteer from 'puppeteer-core'

const EDGE_PATH =
  process.env.EDGE_PATH ?? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const SSO_SECRET = process.env.SSO_SECRET ?? 'dev-only-sso-secret-0123456789abcdef'
const ADMIN_EMAIL = process.env.ADMIN_EMAIL ?? 'admin@example.com'
const CDP_URL = process.env.CDP_URL

const log = (message) => console.log(`[smoke-p3] ${message}`)

function base64url(value) {
  return Buffer.from(value).toString('base64url')
}

function ssoToken(email) {
  const header = base64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = base64url(
    JSON.stringify({
      email,
      name: '管理员',
      exp: Math.floor(Date.now() / 1000) + 600,
    }),
  )
  const signature = crypto
    .createHmac('sha256', SSO_SECRET)
    .update(`${header}.${payload}`)
    .digest('base64url')
  return `${header}.${payload}.${signature}`
}

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
        `--user-data-dir=${fs.mkdtempSync(path.join(process.env.TEMP ?? '/tmp', 'feedlog-p3-'))}`,
      ],
    })

try {
  const page = await browser.newPage()
  await page.setViewport({ width: 1280, height: 1000 })
  page.on('console', (message) => {
    if (message.type() === 'error') console.log(`[browser] ${message.text()}`)
  })

  // 1. SSO 登录（302 到看板页，HttpOnly cookie 落盘）
  const token = ssoToken(ADMIN_EMAIL)
  await page.goto(
    `${BASE_URL}/api/sso/jwt?token=${encodeURIComponent(token)}&return_to=/b/product`,
    { waitUntil: 'networkidle2' },
  )
  await page.waitForSelector('.admin-badge', { timeout: 15000 })
  log('SSO 登录成功，头部显示管理员徽标')

  // 2. 打开第一条反馈并变更状态
  await page.click('.post-title-link')
  await page.waitForSelector('.status-select')
  await page.select('.status-select', 'planned')
  await page.waitForSelector('.status-planned', { timeout: 10000 })
  log('管理员状态流转 planned 生效')

  // 3. 评论
  const commentText = `冒烟评论 ${Date.now()}`
  await page.type('.comment-form textarea', commentText)
  await page.click('.comment-form .button-primary')
  await page.waitForFunction(
    (text) =>
      [...document.querySelectorAll('.comment-content')].some((node) =>
        node.textContent?.includes(text),
      ),
    { timeout: 15000 },
    commentText,
  )
  log('评论发布并出现在列表中')

  // 4. 回复（二层）
  const replyText = `冒烟回复 ${Date.now()}`
  await page.click('.comment-card .comment-action')
  await page.waitForSelector('.reply-chip')
  await page.type('.comment-form textarea', replyText)
  await page.click('.comment-form .button-primary')
  await page.waitForFunction(
    (text) =>
      [...document.querySelectorAll('.comment-content')].some((node) =>
        node.textContent?.includes(text),
      ),
    { timeout: 15000 },
    replyText,
  )
  const childCount = await page.$$eval('.comment-children .comment-card', (nodes) => nodes.length)
  if (childCount < 1) throw new Error('回复未出现在子节点中')
  log('楼中楼回复渲染正常')

  // 5. 更新日志：新建草稿并发布
  await page.goto(`${BASE_URL}/changelog`, { waitUntil: 'networkidle2' })
  await page.waitForSelector('a[href="/changelog/new"]')
  await page.click('a[href="/changelog/new"]')
  await page.waitForSelector('.tiptap')
  const changelogTitle = `P3 冒烟发布 ${Date.now()}`
  await page.type('.field-input', changelogTitle)
  await page.click('.tiptap')
  await page.type('.tiptap', '这是 P3 冒烟测试自动创建的更新日志。')
  for (const button of await page.$$('button')) {
    const text = await button.evaluate((element) => element.textContent ?? '')
    if (text.trim() === '保存') {
      await button.click()
      break
    }
  }
  await page.waitForFunction(() => /\/changelog\/[0-9a-f-]+$/.test(location.pathname), {
    timeout: 15000,
  })
  await page.waitForSelector('.detail-admin-bar')
  const publishButton = await page.waitForSelector('.detail-admin-actions button')
  await publishButton.click()
  await page.waitForFunction(
    () => document.querySelector('.detail-admin-bar')?.textContent?.includes('已发布'),
    { timeout: 10000 },
  )
  log('更新日志草稿创建并发布成功')

  await page.goto(`${BASE_URL}/changelog`, { waitUntil: 'networkidle2' })
  await page.waitForFunction(
    (title) => document.body.textContent?.includes(title),
    { timeout: 10000 },
    changelogTitle,
  )
  log('公开列表可见新发布的更新日志')

  console.log('\nP3 冒烟测试通过')
} finally {
  await browser.close()
}

/**
 * A2/A4 冒烟：access cookie 失效后自动 refresh 重放；POST 登录不把 token 放进 URL。
 *
 *   pnpm smoke:session
 */
import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import puppeteer from 'puppeteer-core'

const EDGE_PATH =
  process.env.EDGE_PATH ??
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const SSO_SECRET =
  process.env.SSO_SECRET ?? 'dev-only-sso-secret-0123456789abcdef'
const ADMIN_EMAIL = process.env.ADMIN_EMAIL ?? 'admin@example.com'
const CDP_URL = process.env.CDP_URL

const log = (message) => console.log(`[smoke-session] ${message}`)

function base64url(value) {
  return Buffer.from(value).toString('base64url')
}

function ssoToken(email) {
  const header = base64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = base64url(
    JSON.stringify({
      email,
      name: '会话测试',
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
        `--user-data-dir=${fs.mkdtempSync(path.join(process.env.TEMP ?? '/tmp', 'feedlog-session-'))}`,
      ],
    })

try {
  const page = await browser.newPage()
  await page.setViewport({ width: 1280, height: 1000 })
  page.on('console', (message) => {
    if (message.type() === 'error') console.log(`[browser] ${message.text()}`)
  })

  // 1. 开发快速登录并打开一条反馈
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle2' })
  const loggedIn = await page.evaluate(async (email) => {
    const response = await fetch('/api/v1/auth/dev-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, name: '会话测试' }),
    })
    return response.ok
  }, ADMIN_EMAIL)
  if (!loggedIn) throw new Error('开发快速登录失败')
  await page.goto(`${BASE_URL}/b/product`, { waitUntil: 'networkidle2' })
  await page.click('.post-title-link')
  await page.waitForSelector('.status-select')

  // 2. 把 access cookie 换成无效值，模拟 access 过期
  const cdp = await page.createCDPSession()
  await cdp.send('Network.enable')
  await cdp.send('Network.deleteCookies', { name: 'feedlog_access', url: `${BASE_URL}/` })
  await cdp.send('Network.setCookie', {
    name: 'feedlog_access',
    value: 'expired.invalid.token',
    url: `${BASE_URL}/`,
    httpOnly: true,
    sameSite: 'Lax',
  })
  log('已注入失效 access cookie')

  // 3. 触发需要登录的状态变更：前端应 refresh 后自动重放
  const current = await page.$eval('.status-select', (element) => element.value)
  const target = current === 'in_progress' ? 'planned' : 'in_progress'
  await page.select('.status-select', target)
  await page.waitForSelector(`.status-${target}`, { timeout: 15000 })
  log(`自动续期生效：状态已变更为 ${target}`)

  const me = await page.evaluate(async () => {
    const response = await fetch('/api/v1/auth/me')
    return response.json()
  })
  if (!me.authenticated || !me.is_admin) {
    throw new Error(`refresh 后会话异常: ${JSON.stringify(me)}`)
  }
  log('refresh 后仍为管理员会话')

  // 4. 退出后用 POST 方式粘贴 token 登录，token 不进入 URL
  await page.evaluate(() => fetch('/api/v1/auth/logout', { method: 'POST' }))
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle2' })
  const token = ssoToken(ADMIN_EMAIL)
  await page.$eval('.login-token', (element, value) => {
    element.value = value
    element.dispatchEvent(new Event('input', { bubbles: true }))
  }, token)
  for (const button of await page.$$('button')) {
    const text = await button.evaluate((element) => element.textContent ?? '')
    if (text.includes('使用 SSO token 登录')) {
      await button.click()
      break
    }
  }
  await page.waitForSelector('.admin-badge', { timeout: 15000 })
  const finalUrl = page.url()
  if (finalUrl.includes('token=')) throw new Error(`token 泄漏到 URL: ${finalUrl}`)
  log('POST SSO 登录成功，URL 不含 token')

  console.log('\nA2/A4 冒烟测试通过')
} finally {
  await browser.close()
}

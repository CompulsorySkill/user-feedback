/**
 * 样式一致性检查：每页字号 ≤ 3 种、操作按钮高度一致。
 *
 *   pnpm check:style
 */
import fs from 'node:fs'
import path from 'node:path'
import puppeteer from 'puppeteer-core'

const EDGE_PATH =
  process.env.EDGE_PATH ??
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const CDP_URL = process.env.CDP_URL

async function api(pathname) {
  const response = await fetch(`${BASE_URL}${pathname}`)
  if (!response.ok) throw new Error(`fetch ${pathname} -> ${response.status}`)
  return response.json()
}

const [boards, productPage, changelogs] = await Promise.all([
  api('/api/v1/boards'),
  api('/api/v1/boards/product/posts?limit=1'),
  api('/api/v1/changelogs?limit=1'),
])
const postId = productPage.items[0]?.id
const changelogId = changelogs.items[0]?.id
if (!postId || !changelogId) throw new Error('缺少用于检查的种子数据')

const routes = [
  ['首页', '/'],
  ['看板', `/b/${boards[0].slug}`],
  ['反馈详情', `/post/${postId}`],
  ['发布反馈', `/b/${boards[0].slug}/new`],
  ['编辑反馈', `/post/${postId}/edit`],
  ['登录', '/login'],
  ['更新日志', '/changelog'],
  ['更新日志详情', `/changelog/${changelogId}`],
]
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
        `--user-data-dir=${fs.mkdtempSync(path.join(process.env.TEMP ?? '/tmp', 'feedlog-style-'))}`,
      ],
    })

let failed = false
try {
  const page = await browser.newPage()
  await page.setViewport({ width: 1280, height: 1000 })

  // 若能开发快速登录为管理员，则一并检查管理页面。
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle2' })
  const isAdmin = await page.evaluate(async () => {
    try {
      const response = await fetch('/api/v1/auth/dev-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'admin@example.com' }),
      })
      if (!response.ok) return false
      return Boolean((await response.json()).is_admin)
    } catch {
      return false
    }
  })
  if (isAdmin) {
    routes.push(
      ['反馈详情（管理员）', `/post/${postId}`],
      ['新建更新日志', '/changelog/new'],
      ['编辑更新日志', `/changelog/${changelogId}/edit`],
    )
  }

  for (const [label, route] of routes) {
    await page.goto(`${BASE_URL}${route}`, { waitUntil: 'networkidle2' })
    await new Promise((resolve) => setTimeout(resolve, 300))

    const result = await page.evaluate(() => {
      const visibleText = [...document.querySelectorAll('body *')].filter((element) => {
        const style = getComputedStyle(element)
        if (style.display === 'none' || style.visibility === 'hidden') return false
        const rect = element.getBoundingClientRect()
        if (rect.width === 0 || rect.height === 0) return false
        return [...element.childNodes].some(
          (node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim(),
        )
      })

      const sizeMap = new Map()
      for (const element of visibleText) {
        const size = getComputedStyle(element).fontSize
        if (!sizeMap.has(size)) {
          sizeMap.set(size, (element.textContent ?? '').trim().slice(0, 24))
        }
      }

      const buttonHeights = [
        ...new Set(
          [...document.querySelectorAll('.button')].map((element) =>
            Math.round(element.getBoundingClientRect().height),
          ),
        ),
      ]
      const toolHeights = [
        ...new Set(
          [...document.querySelectorAll('.tool-button')].map((element) =>
            Math.round(element.getBoundingClientRect().height),
          ),
        ),
      ]
      const chipHeights = [
        ...new Set(
          [...document.querySelectorAll('.filter-chip, .sort-group, .vote-button')].map(
            (element) => Math.round(element.getBoundingClientRect().height),
          ),
        ),
      ]

      return {
        sizes: [...sizeMap.keys()],
        samples: Object.fromEntries(sizeMap),
        buttonHeights,
        toolHeights,
        chipHeights,
      }
    })

    const sizeCount = result.sizes.length
    const okSizes = sizeCount <= 3
    const okButtons = result.buttonHeights.length <= 1
    const okTools = result.toolHeights.length <= 1
    const okChips = result.chipHeights.length <= 1
    if (!okSizes || !okButtons || !okTools || !okChips) failed = true

    console.log(
      `${okSizes && okButtons && okTools && okChips ? 'PASS' : 'FAIL'} ${label}: 字号 ${sizeCount} 种 [${result.sizes.join(', ')}] | 按钮高度 ${JSON.stringify(result.buttonHeights)} | 工具按钮 ${JSON.stringify(result.toolHeights)} | 胶囊 ${JSON.stringify(result.chipHeights)}`,
    )
    if (!okSizes) console.log('  sizes:', result.samples)
  }
} finally {
  await browser.close()
}

if (failed) {
  console.error('\n样式一致性检查未通过')
  process.exit(1)
}
console.log('\n样式一致性检查通过')

/**
 * P2 浏览器冒烟测试：编辑器发帖 + 图片直传 + 投票。
 *
 *   pnpm smoke:p2
 *
 * 依赖本机 Edge（可用 EDGE_PATH 覆盖）与已启动的本地服务：
 * backend:8000 / vite:5173 / rustfs:9000。
 */
import fs from 'node:fs'
import path from 'node:path'
import puppeteer from 'puppeteer-core'

const EDGE_PATH =
  process.env.EDGE_PATH ?? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const COVER = path.resolve('../backend/.dev-storage/uploads/demo-cover.png')

const log = (message) => console.log(`[smoke] ${message}`)

if (!fs.existsSync(EDGE_PATH)) throw new Error(`找不到浏览器: ${EDGE_PATH}`)
if (!fs.existsSync(COVER)) throw new Error(`找不到测试图片: ${COVER}`)

const CDP_URL = process.env.CDP_URL

function tempProfile() {
  return fs.mkdtempSync(path.join(process.env.TEMP ?? '/tmp', 'feedlog-edge-'))
}

const browser = CDP_URL
  ? await puppeteer.connect({ browserURL: CDP_URL })
  : await puppeteer.launch({
      executablePath: EDGE_PATH,
      headless: true,
      pipe: false,
      dumpio: false,
      args: [
        '--headless=new',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-gpu',
        '--disable-dev-shm-usage',
        '--window-size=1280,1000',
        `--user-data-dir=${tempProfile()}`,
      ],
    })

try {
  const page = await browser.newPage()
  await page.setViewport({ width: 1280, height: 1000 })
  page.on('console', (message) => {
    if (message.type() === 'error') console.log(`[browser] ${message.text()}`)
  })

  // 1. 打开发帖页
  await page.goto(`${BASE_URL}/b/product/new`, { waitUntil: 'networkidle2' })
  await page.waitForSelector('.tiptap')
  log('发帖页已加载')

  // 2. 填标题与正文
  const title = `浏览器直传验收 ${Date.now()}`
  const nickname = '冒烟测试用户'
  await page.type('input[placeholder*="路过的产品经理"]', nickname)
  await page.type('input[placeholder*="一句话"]', title)
  await page.click('.tiptap')
  await page.type('.tiptap', '这是浏览器经 presigned PUT 直传图片后发布的验收反馈。')

  const envChecked = await page.$eval('.env-toggle input', (element) => element.checked)
  if (!envChecked) throw new Error('环境信息勾选框应默认勾选')

  // 3. 通过编辑器文件输入上传图片（触发与工具栏相同的 onChange 流程）
  const fileInput = await page.$('input[type=file]')
  if (!fileInput) throw new Error('未找到文件输入')
  await fileInput.uploadFile(COVER)

  // 4. 等待直传完成并插入 image 节点
  await page.waitForFunction(
    () => {
      const image = document.querySelector('.tiptap img')
      return image instanceof HTMLImageElement && image.complete && image.naturalWidth > 0
    },
    { timeout: 20000 },
  )
  const imageSrc = await page.$eval('.tiptap img', (element) => element.getAttribute('src'))
  log(`图片已插入: ${imageSrc}`)

  // 5. 发布并跳转详情
  const publishButtons = await page.$$('button')
  for (const button of publishButtons) {
    const text = await button.evaluate((element) => element.textContent ?? '')
    if (text.includes('发布反馈')) {
      await button.click()
      break
    }
  }
  await page.waitForFunction(() => location.pathname.startsWith('/post/'), { timeout: 15000 })
  await page.waitForSelector('.post-detail h1')
  const heading = await page.$eval('.post-detail h1', (element) => element.textContent?.trim())
  if (heading !== title) throw new Error(`标题不一致: ${heading} !== ${title}`)
  const renderedImage = await page.$eval('.rich-text img', (element) => ({
    width: element.naturalWidth,
    src: element.getAttribute('src'),
  }))
  if (!renderedImage.src?.startsWith('/storage/') || renderedImage.width === 0) {
    throw new Error(`详情页图片未渲染: ${JSON.stringify(renderedImage)}`)
  }

  // 5.1 昵称标注「匿名」+ 环境信息面板
  const authorText = await page.$eval('.author-tag', (element) => element.textContent ?? '')
  if (!authorText.includes(nickname) || !authorText.includes('匿名')) {
    throw new Error(`匿名昵称展示不正确: ${authorText}`)
  }
  const envSummary = await page.$eval('.env-panel summary', (element) => element.textContent ?? '')
  if (!envSummary.includes('浏览器')) throw new Error('缺少环境信息面板')
  await page.click('.env-panel summary')
  const uaText = await page.$eval('.env-grid', (element) => element.textContent ?? '')
  if (!uaText.includes('Mozilla')) throw new Error('环境信息未展示 User Agent')
  log('匿名昵称与浏览器环境信息展示正常')
  log(`发布成功，详情页图片渲染正常 (${renderedImage.width}px)`)

  // 6. 投票（乐观更新 -> 服务端确认）与取消
  const voteButton = await page.waitForSelector('.vote-button')
  const countBefore = await voteButton.$eval('.vote-count', (element) => element.textContent)
  await voteButton.click()
  await page.waitForFunction(
    (expected) => {
      const button = document.querySelector('.vote-button')
      return (
        button?.classList.contains('is-voted') &&
        button.querySelector('.vote-count')?.textContent === String(expected)
      )
    },
    { polling: 200, timeout: 15000 },
    Number(countBefore) + 1,
  )
  const countAfter = await page.$eval('.vote-button .vote-count', (element) => element.textContent)
  if (Number(countAfter) !== Number(countBefore) + 1) {
    throw new Error(`投票计数未更新: ${countBefore} -> ${countAfter}`)
  }
  await page.click('.vote-button')
  await page.waitForFunction(
    (expected) => {
      const button = document.querySelector('.vote-button')
      return (
        button !== null &&
        !button.classList.contains('is-voted') &&
        button.querySelector('.vote-count')?.textContent === String(expected)
      )
    },
    { polling: 200, timeout: 15000 },
    Number(countBefore),
  )
  log('投票 / 取消投票均通过')

  console.log('\nP2 冒烟测试通过')
} finally {
  await browser.close()
}

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

// vitest 以 frontend/ 为工作目录
const read = (rel: string): string => readFileSync(join(process.cwd(), rel), 'utf8');

/**
 * 子路径部署（BASE_PATH）依赖三件事同时成立，任一被改回绝对路径都会让
 * 「公司反代只转发 /feedback/*」时静态资源与懒加载 chunk 404。
 */
describe('子路径部署的构建/启动约定', () => {
  it('构建产物用相对路径（vite base 为空）', () => {
    expect(read('vite.config.ts')).toMatch(/^\s*base: '',?$/m);
  });

  it('index 模板在最前注入 <base href> 与运行时前缀', () => {
    const script = read('scripts/runtime-index.mjs');
    // 忽略字符串转义风格差异（oxfmt 会把 \" 变成 '）
    const plain = script.replace(/\\/g, '');
    expect(plain).toContain('<base href="__BASE__/">');
    expect(plain).toContain("window.__FEEDBACK_BASE__='__BASE__'");
    // <base> 只对解析顺序在它之后的相对 URL 生效，必须贴在 <head> 后面
    expect(script).toContain("html.replace('<head>', `<head>${marker}`)");
  });

  it('启动脚本只替换 __BASE__，不再改写 "="/ 绝对地址', () => {
    const entry = read('docker-entrypoint.sh');
    expect(entry).toContain('s|__BASE__|$BASE|g');
    expect(entry).not.toContain('="\\$BASE/|g');
  });
});

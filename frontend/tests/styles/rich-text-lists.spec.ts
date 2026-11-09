import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

// 守卫：Tailwind preflight 把 ul/ol 的 list-style 置为 none，富文本正文与编辑器
// 都靠这两条规则把序号/圆点加回来；丢了是「列表变成一段行文字」而其余单测全绿。
const read = (p: string) => readFileSync(resolve(process.cwd(), p), 'utf8');

describe('列表标记', () => {
  it('富文本正文的 ul/ol 有 list-style', () => {
    const css = read('src/style.css');
    expect(css).toMatch(/ul\.rt-list\s*\{[^}]*list-style:\s*disc;/);
    expect(css).toMatch(/ol\.rt-list\s*\{[^}]*list-style:\s*decimal;/);
  });

  it('编辑器里的 ul/ol 有 list-style', () => {
    const css = read('src/styles/write-path.css');
    expect(css).toMatch(/\.tiptap ul\s*\{[^}]*list-style:\s*disc;/);
    expect(css).toMatch(/\.tiptap ol\s*\{[^}]*list-style:\s*decimal;/);
  });
});

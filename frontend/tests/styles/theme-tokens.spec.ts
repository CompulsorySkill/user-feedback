import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

// 守卫：shadcn 初始化/重新拉取会把这组变量就地覆盖成 zinc 默认值，业务 CSS 全靠它们，
// 一旦被顶掉是「全站主色变白」而其余单测全绿。
const css = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf8');

describe('style.css 主题基线', () => {
  it('shadcn 语义变量持有项目配色（不是 zinc 默认值）', () => {
    expect(css).toMatch(/--background:\s*#f6f7f9;/);
    expect(css).toMatch(/--primary:\s*#4f46e5;/);
    expect(css).toMatch(/--border:\s*#e4e6eb;/);
    expect(css).toMatch(/--radius:\s*14px;/);
  });

  it('字体自托管，不引 Google Fonts', () => {
    expect(css).not.toContain('fonts.googleapis.com');
    expect(css).toMatch(/--font-sans:\s*'Noto Sans'/);
  });

  it('深色取值只在 .dark 块里，不再用 media query（否则手动切换失效）', () => {
    expect(css).not.toContain('prefers-color-scheme');
    expect(css).toMatch(/^\.dark \{/m);
  });

  it('旧样式别名只指向 shadcn 变量，不自我引用', () => {
    const semantic = [
      'background',
      'foreground',
      'card',
      'popover',
      'primary',
      'secondary',
      'muted',
      'muted-foreground',
      'accent',
      'accent-foreground',
      'destructive',
      'border',
      'input',
      'ring',
    ];
    const aliases = [
      ...css.matchAll(
        /^\s{2}--(bg|surface|surface-muted|text|text-muted|brand|brand-soft|line|line-strong|error):\s*var\(--([a-z-]+)\);/gm,
      ),
    ];
    expect(aliases.length).toBeGreaterThanOrEqual(10);
    for (const [, alias, target] of aliases) {
      expect(semantic, `--${alias} → --${target}`).toContain(target);
    }
  });
});

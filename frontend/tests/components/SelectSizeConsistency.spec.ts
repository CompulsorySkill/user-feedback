import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

// 守卫：SelectItem 的字号/行高由自己的 size 决定，不继承 SelectTrigger。
// 触发器等 32px 密集行用 size="sm"（text-xs），弹层选项若漏写就是 16px 错位。
const SRC = resolve(process.cwd(), 'src');

function vueFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return vueFiles(path);
    return name.endsWith('.vue') ? [path] : [];
  });
}

function sizeOf(tag: string): string {
  return /\bsize="([^"]+)"/.exec(tag)?.[1] ?? 'default';
}

describe('Select 触发器与选项尺寸一致', () => {
  it('每个 Select 的 SelectItem 与 SelectTrigger 同尺寸', () => {
    const mismatches: string[] = [];

    for (const file of vueFiles(SRC)) {
      const source = readFileSync(file, 'utf8');
      for (const block of source.matchAll(/<Select\b[\s\S]*?<\/Select>/g)) {
        const trigger = /<SelectTrigger\b[^>]*>/.exec(block[0])?.[0];
        if (!trigger) continue;
        const triggerSize = sizeOf(trigger);
        for (const [item] of block[0].matchAll(/<SelectItem\b[^>]*>/g)) {
          if (sizeOf(item) !== triggerSize) {
            mismatches.push(`${file.replace(SRC, 'src')}: ${item.split('\n')[0]}`);
          }
        }
      }
    }

    expect(mismatches).toEqual([]);
  });
});

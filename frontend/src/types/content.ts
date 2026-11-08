/** Tiptap / ProseMirror JSON 的最小类型定义。 */
export interface JSONMark {
  type: string;
  attrs?: Record<string, unknown>;
}

export interface JSONContent {
  type?: string;
  attrs?: Record<string, unknown>;
  content?: JSONContent[];
  marks?: JSONMark[];
  text?: string;
}

export function attrString(node: JSONContent, name: string): string | null {
  const value = node.attrs?.[name];
  return typeof value === 'string' && value.length > 0 ? value : null;
}

export function attrNumber(node: JSONContent, name: string, fallback: number): number {
  const value = node.attrs?.[name];
  return typeof value === 'number' ? value : fallback;
}

/** 富文本纯文本长度（含 mention 展示名），与后端校验口径一致。 */
export function contentTextLength(node: JSONContent | null): number {
  return contentPlainText(node).length;
}

/** 是否包含图片 / 视频；媒体单独存在时也算有效内容。 */
export function contentHasMedia(node: JSONContent | null): boolean {
  if (!node) return false;
  if (node.type === 'image' || node.type === 'video') return true;
  return (node.content ?? []).some(contentHasMedia);
}

/** 提取纯文本（含 mention 展示名），用于长度统计与空内容判断。 */
export function contentPlainText(node: JSONContent | null): string {
  if (!node) return '';
  if (node.type === 'mention') {
    const label = node.attrs?.label;
    return typeof label === 'string' ? `@${label}` : '';
  }
  return (node.text ?? '') + (node.content ?? []).map(contentPlainText).join('');
}

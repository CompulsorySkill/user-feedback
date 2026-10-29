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

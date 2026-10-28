/** 剪贴板里的截图 / 图片文件；其他类型（文本、HTML、视频）忽略。 */
export function imageFilesFromClipboard(data: Pick<DataTransfer, 'files'> | null): File[] {
  if (!data) return []
  return Array.from(data.files ?? []).filter((file) => file.type.startsWith('image/'))
}

/** 将源数据中的数字/占位作者转为可读展示名 */
export function formatAuthor(author) {
  const raw = (author || '').trim();
  if (!raw) return '佚名';
  if (/^\d+$/.test(raw)) {
    const short = raw.replace(/^0+/, '') || raw;
    return `网络诗人 · ${short}`;
  }
  if (/^[a-zA-Z0-9._-]{1,8}$/.test(raw)) return '佚名';
  return raw;
}

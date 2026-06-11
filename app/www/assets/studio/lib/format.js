export function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

export function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes)) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

export function formatDuration(ms) {
  const value = Number(ms);
  if (!Number.isFinite(value)) return '-';
  if (value < 1000) return `${value}ms`;
  const seconds = value / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes}m ${rest}s`;
}

export function shortId(value, length = 8) {
  if (!value) return '-';
  return String(value).slice(0, length);
}

export function truncateText(value, max = 120) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (text.length <= max) return text;
  return `${text.slice(0, Math.max(0, max - 1))}…`;
}

export function extensionFromName(value, fallback = '') {
  const name = String(value || '');
  const match = name.match(/\.([a-z0-9]{2,8})$/i);
  return match ? `.${match[1].toLowerCase()}` : fallback;
}

export function safeFilenamePart(value, fallback = 'asset') {
  const cleaned = String(value || '')
    .normalize('NFKD')
    .replace(/[^\w.-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^[-.]+|[-.]+$/g, '')
    .slice(0, 48);
  return cleaned || fallback;
}

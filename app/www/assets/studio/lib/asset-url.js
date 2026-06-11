import { extensionFromName, safeFilenamePart, shortId, truncateText } from './format.js';

const SAFE_ASSET_PREFIXES = ['/generated/', '/uploads/'];

export function isSafeAssetUrl(value) {
  try {
    const parsed = new URL(String(value || ''), window.location.origin);
    return parsed.origin === window.location.origin &&
      SAFE_ASSET_PREFIXES.some((prefix) => parsed.pathname.startsWith(prefix));
  } catch (_) {
    return false;
  }
}

export function safeAssetHref(value) {
  if (!isSafeAssetUrl(value)) return '';
  return new URL(String(value), window.location.origin).pathname;
}

export function isImageAsset(asset) {
  const type = String(asset?.media_type || '').toLowerCase();
  return type === 'image' || type.startsWith('image/');
}

export function isVideoAsset(asset) {
  const type = String(asset?.media_type || '').toLowerCase();
  return type === 'video' || type.startsWith('video/');
}

export function assetDisplayName(asset) {
  if (asset?.display_name) return truncateText(asset.display_name, 72);
  if (asset?.prompt) return truncateText(asset.prompt, 72);
  const kind = isVideoAsset(asset) ? 'video' : 'image';
  const source = asset?.source === 'upload' ? 'upload' : 'generated';
  return `AngeMedia ${source} ${kind} ${shortId(asset?.id, 6)}`;
}

export function buildAssetDownloadName(asset) {
  const ext = extensionFromName(asset?.filename || asset?.url_path, isVideoAsset(asset) ? '.mp4' : '.png');
  const kind = isVideoAsset(asset) ? 'video' : 'image';
  const title = safeFilenamePart(asset?.display_name || asset?.prompt || `${kind}-${shortId(asset?.id, 8)}`, kind);
  return `angemedia-${title}${ext}`;
}

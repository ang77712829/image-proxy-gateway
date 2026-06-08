import { api } from '../api.js';
import { t } from '../i18n.js';

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

function formatSize(bytes) {
  if (!bytes && bytes !== 0) return '-';
  return `${bytes} B`;
}

function isSafeAssetUrl(url) {
  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.origin !== window.location.origin) return false;
    return parsed.pathname.startsWith('/generated/') ||
           parsed.pathname.startsWith('/uploads/');
  } catch (_) {
    return false;
  }
}

function isImageAsset(asset) {
  const type = String(asset.media_type || '').toLowerCase();
  return type === 'image' || type.startsWith('image/');
}

function createPreviewFallback() {
  const fallback = document.createElement('p');
  fallback.textContent = t('assets.unavailable');
  fallback.style.color = '#888';
  fallback.style.fontStyle = 'italic';
  fallback.style.fontSize = '12px';
  return fallback;
}

export async function render() {
  const content = document.getElementById('content');
  content.innerHTML = '';

  const card = document.createElement('div');
  card.className = 'card';

  const h2 = document.createElement('h2');
  h2.textContent = t('assets.title');
  card.appendChild(h2);

  const loading = document.createElement('p');
  loading.textContent = t('assets.loading');
  loading.style.color = '#888';
  card.appendChild(loading);

  content.appendChild(card);

  try {
    const result = await api.get('/assets?limit=20&offset=0');
    loading.remove();

    // 防御式解析：不假设 data 一定是数组
    const assets = Array.isArray(result?.data) ? result.data : [];

    if (assets.length === 0) {
      const empty = document.createElement('p');
      empty.textContent = t('assets.empty');
      empty.style.color = '#888';
      card.appendChild(empty);
      return;
    }

    const list = document.createElement('div');
    list.style.display = 'grid';
    list.style.gridTemplateColumns = 'repeat(auto-fill, minmax(250px, 1fr))';
    list.style.gap = '16px';

    assets.forEach(asset => {
      const item = document.createElement('div');
      item.className = 'card';
      item.style.padding = '12px';

      // 缩略图预览（安全校验 + 加载失败 fallback）
      if (isImageAsset(asset) && asset.url_path) {
        const fallback = createPreviewFallback();

        if (isSafeAssetUrl(asset.url_path)) {
          const img = document.createElement('img');
          img.src = asset.url_path;
          img.alt = asset.filename || t('assets.preview');
          img.style.maxWidth = '100%';
          img.style.maxHeight = '150px';
          img.style.borderRadius = '4px';
          img.style.marginBottom = '8px';
          img.style.objectFit = 'contain';

          // 图片加载失败时：移除 img，显示 fallback
          img.addEventListener('error', () => {
            img.remove();
            fallback.hidden = false;
          });

          // URL 安全时：先隐藏 fallback，只显示 img
          fallback.hidden = true;
          item.appendChild(img);
          item.appendChild(fallback);
        } else {
          // URL 不安全：直接显示 fallback
          item.appendChild(fallback);
        }
      }

      // Filename
      const filename = document.createElement('p');
      filename.textContent = asset.filename || '-';
      filename.style.fontWeight = '600';
      filename.style.marginBottom = '4px';
      filename.style.wordBreak = 'break-all';
      item.appendChild(filename);

      // Metadata row
      const meta = document.createElement('div');
      meta.style.fontSize = '12px';
      meta.style.color = '#666';

      const typeKey = `assets.${asset.media_type}`;
      const typeText = t(typeKey) !== typeKey ? t(typeKey) : asset.media_type || t('assets.unknown');
      const sourceKey = `assets.${asset.source}`;
      const sourceText = t(sourceKey) !== sourceKey ? t(sourceKey) : asset.source || '-';

      const fields = [
        `${t('assets.type')}: ${typeText}`,
        `${t('assets.source')}: ${sourceText}`,
        `${t('assets.created')}: ${formatDate(asset.created_at)}`,
        `${t('assets.size')}: ${formatSize(asset.size)}`,
      ];

      if (asset.job_id) {
        fields.push(`${t('assets.jobId')}: ${asset.job_id.substring(0, 8)}`);
      }

      const metaText = document.createElement('p');
      metaText.textContent = fields.join(' | ');
      metaText.style.margin = '2px 0';
      meta.appendChild(metaText);

      item.appendChild(meta);
      list.appendChild(item);
    });

    card.appendChild(list);
  } catch (err) {
    loading.remove();
    const errorText = document.createElement('p');
    errorText.textContent = t('assets.error');
    errorText.className = 'error-text';
    card.appendChild(errorText);
  }
}

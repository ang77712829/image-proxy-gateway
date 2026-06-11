import { api } from '../../api.js';
import { t } from '../../i18n.js';
import { button, linkButton } from '../../components/buttons.js';
import { badge } from '../../components/badges.js';
import { el, mount } from '../../components/dom.js';
import { select } from '../../components/forms.js';
import { confirmModal } from '../../components/modal.js';
import { pageHeader, panel, metricCard, metaGrid } from '../../components/page.js';
import { emptyState, errorState, loadingState } from '../../components/states.js';
import { toast } from '../../components/toast.js';
import { assetDisplayName, buildAssetDownloadName, isImageAsset, isVideoAsset, safeAssetHref } from '../../lib/asset-url.js';
import { formatBytes, formatDate, formatDuration, shortId, truncateText } from '../../lib/format.js';

let allAssets = [];
let mediaFilter = '';
let sourceFilter = '';

function dataArray(result) {
  return Array.isArray(result?.data) ? result.data : [];
}

function typeLabel(asset) {
  if (isImageAsset(asset)) return t('assets.image');
  if (isVideoAsset(asset)) return t('assets.video');
  return asset.media_type || '-';
}

function sourceLabel(asset) {
  if (asset.source === 'generated') return t('assets.generated');
  if (asset.source === 'upload') return t('assets.upload');
  return asset.source || '-';
}

function filteredAssets() {
  return allAssets.filter((asset) => {
    if (mediaFilter && asset.media_type !== mediaFilter) return false;
    if (sourceFilter && asset.source !== sourceFilter) return false;
    return true;
  });
}

function previewNode(asset) {
  const href = safeAssetHref(asset.url_path);
  if (!href) {
    return el('div', { class: 'asset-thumb' }, emptyState(t('assets.unavailable')));
  }
  if (isImageAsset(asset)) {
    return el('a', { class: 'asset-thumb', href, target: '_blank', rel: 'noopener noreferrer' },
      el('img', { src: href, alt: assetDisplayName(asset), loading: 'lazy' }),
    );
  }
  if (isVideoAsset(asset)) {
    return el('div', { class: 'asset-thumb' },
      el('video', { src: href, controls: true, preload: 'metadata' }),
    );
  }
  return el('div', { class: 'asset-thumb' }, emptyState(t('assets.unavailable')));
}

function assetActions(asset, reload) {
  const href = safeAssetHref(asset.url_path);
  const actions = [];
  if (href) {
    actions.push(linkButton(t('common.download'), href, {
      size: 'sm',
      variant: 'primary',
      download: buildAssetDownloadName(asset),
    }));
    actions.push(linkButton(t('common.open'), href, { size: 'sm', target: '_blank' }));
  } else {
    actions.push(button(t('common.download'), {
      size: 'sm',
      onClick: () => toast(t('assets.downloadUnavailable'), 'error'),
    }));
  }
  actions.push(button(t('common.edit'), {
    size: 'sm',
    onClick: () => toast(t('assets.editUnavailable'), 'info'),
  }));
  actions.push(button(t('common.delete'), {
    size: 'sm',
    variant: 'danger',
    onClick: () => confirmModal({
      title: t('assets.deleteTitle'),
      message: t('assets.deleteMessage'),
      confirmLabel: t('common.delete'),
      cancelLabel: t('common.cancel'),
      danger: true,
      onConfirm: async () => {
        try {
          await api.delete(`/assets/${encodeURIComponent(asset.id)}`);
          toast(t('assets.deleteSuccess'), 'success');
          await reload();
        } catch (_) {
          toast(t('assets.deleteError'), 'error');
        }
      },
    }),
  }));
  return el('div', { class: 'action-row' }, actions);
}

function assetCard(asset, reload) {
  const title = assetDisplayName(asset);
  return el('article', { class: 'asset-card' },
    previewNode(asset),
    el('div', { class: 'asset-card-header' },
      el('div', {},
        el('p', { class: 'card-title' }, title),
        el('p', { class: 'asset-original-name' }, `${t('assets.filename')}: ${asset.filename || '-'}`),
      ),
      badge(typeLabel(asset), isImageAsset(asset) ? 'info' : 'violet'),
    ),
    metaGrid([
      { label: t('assets.source'), value: sourceLabel(asset) },
      { label: t('assets.size'), value: formatBytes(asset.size) },
      { label: t('assets.provider'), value: asset.provider || '-' },
      { label: t('assets.model'), value: asset.model || '-' },
      { label: t('assets.jobId'), value: asset.job_id ? shortId(asset.job_id) : '-' },
      { label: t('assets.created'), value: formatDate(asset.created_at) },
      { label: t('generateImage.duration'), value: asset.duration_ms ? formatDuration(asset.duration_ms) : '' },
    ]),
    asset.prompt ? el('p', { class: 'card-subtitle' }, truncateText(asset.prompt, 140)) : null,
    assetActions(asset, reload),
  );
}

function renderAssets(content, reload) {
  const assets = filteredAssets();
  const imageCount = allAssets.filter(isImageAsset).length;
  const videoCount = allAssets.filter(isVideoAsset).length;
  const totalBytes = allAssets.reduce((sum, item) => sum + (Number(item.size) || 0), 0);

  mount(content,
    pageHeader({
      kicker: t('assets.kicker'),
      title: t('assets.title'),
      subtitle: t('assets.subtitle'),
      actions: [button(t('common.refresh'), { onClick: reload })],
    }),
    el('div', { class: 'metric-grid' },
      metricCard({ label: t('assets.title'), value: String(allAssets.length), meta: t('assets.allTypes'), tone: 'teal' }),
      metricCard({ label: t('assets.image'), value: String(imageCount), meta: t('assets.generated'), tone: 'blue' }),
      metricCard({ label: t('assets.video'), value: String(videoCount), meta: t('assets.upload'), tone: 'violet' }),
      metricCard({ label: t('assets.size'), value: formatBytes(totalBytes), meta: t('assets.source'), tone: 'gold' }),
    ),
    panel({},
      el('div', { class: 'asset-toolbar' },
        el('div', { class: 'asset-filters' },
          select([
            { value: '', label: t('assets.allTypes') },
            { value: 'image', label: t('assets.image') },
            { value: 'video', label: t('assets.video') },
          ], {
            value: mediaFilter,
            onchange: (event) => {
              mediaFilter = event.target.value;
              renderAssets(content, reload);
            },
          }),
          select([
            { value: '', label: t('assets.allSources') },
            { value: 'generated', label: t('assets.generated') },
            { value: 'upload', label: t('assets.upload') },
          ], {
            value: sourceFilter,
            onchange: (event) => {
              sourceFilter = event.target.value;
              renderAssets(content, reload);
            },
          }),
        ),
        badge(`${assets.length} / ${allAssets.length}`, 'muted'),
      ),
      assets.length ?
        el('div', { class: 'asset-grid' }, assets.map((asset) => assetCard(asset, reload))) :
        el('div', { class: 'panel-body' }, emptyState(t('assets.empty'))),
    ),
  );
}

export async function render() {
  const content = document.getElementById('content');

  async function reload() {
    mount(content, loadingState(t('assets.loading')));
    try {
      const result = await api.get('/assets?limit=100&offset=0');
      allAssets = dataArray(result);
      renderAssets(content, reload);
    } catch (_) {
      mount(content,
        pageHeader({ kicker: t('assets.kicker'), title: t('assets.title'), subtitle: t('assets.subtitle') }),
        errorState(t('assets.error')),
      );
    }
  }

  await reload();
}

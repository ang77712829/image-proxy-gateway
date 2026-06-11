import { el } from './dom.js';

export function pageHeader({ kicker = '', title, subtitle = '', actions = [] }) {
  return el('div', { class: 'page-header' },
    el('div', { class: 'page-title-block' },
      kicker ? el('p', { class: 'eyebrow' }, kicker) : null,
      el('h1', { class: 'page-heading' }, title),
      subtitle ? el('p', { class: 'page-subtitle' }, subtitle) : null,
    ),
    actions.length ? el('div', { class: 'page-actions' }, actions) : null,
  );
}

export function panel({ title = '', subtitle = '', className = '', actions = [] } = {}, ...children) {
  return el('section', { class: ['panel', className].filter(Boolean).join(' ') },
    title || subtitle || actions.length ? el('div', { class: 'panel-header' },
      el('div', {},
        title ? el('h2', {}, title) : null,
        subtitle ? el('p', {}, subtitle) : null,
      ),
      actions.length ? el('div', { class: 'panel-actions' }, actions) : null,
    ) : null,
    ...children,
  );
}

export function metricCard({ label, value, meta = '', tone = 'teal', icon = '' }) {
  return el('article', { class: `metric-card metric-${tone}` },
    icon ? el('span', { class: 'metric-icon' }, icon) : el('span', { class: 'metric-dot' }),
    el('p', { class: 'metric-label' }, label),
    el('p', { class: 'metric-value' }, value),
    meta ? el('p', { class: 'metric-meta' }, meta) : null,
  );
}

export function metaGrid(items) {
  return el('dl', { class: 'meta-grid' },
    items.filter((item) => item.value !== undefined && item.value !== null && item.value !== '').map((item) => [
      el('dt', {}, item.label),
      el('dd', {}, String(item.value)),
    ]).flat(),
  );
}

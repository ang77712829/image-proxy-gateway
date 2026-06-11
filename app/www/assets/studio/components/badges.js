import { el } from './dom.js';

const STATUS_CLASS = {
  succeeded: 'success',
  completed: 'success',
  running: 'info',
  queued: 'warning',
  pending: 'warning',
  failed: 'danger',
  canceled: 'muted',
  enabled: 'success',
  disabled: 'muted',
  revoked: 'danger',
};

export function badge(label, tone = 'muted') {
  return el('span', { class: `badge badge-${tone}` }, label);
}

export function statusBadge(status, label = '') {
  const tone = STATUS_CLASS[String(status || '').toLowerCase()] || 'muted';
  return badge(label || status || '-', tone);
}

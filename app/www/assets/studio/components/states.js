import { el } from './dom.js';

export function loadingState(message) {
  return el('div', { class: 'state state-loading' },
    el('span', { class: 'loader' }),
    el('p', {}, message),
  );
}

export function emptyState(title, message = '') {
  return el('div', { class: 'state' },
    el('p', { class: 'state-title' }, title),
    message ? el('p', { class: 'state-copy' }, message) : null,
  );
}

export function errorState(title, message = '') {
  return el('div', { class: 'state state-error' },
    el('p', { class: 'state-title' }, title),
    message ? el('p', { class: 'state-copy' }, message) : null,
  );
}

export function unavailableState(title, message) {
  return el('div', { class: 'state state-unavailable' },
    el('p', { class: 'state-title' }, title),
    el('p', { class: 'state-copy' }, message),
  );
}

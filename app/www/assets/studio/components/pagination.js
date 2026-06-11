import { el } from './dom.js';

export function pageCount(total, pageSize) {
  return Math.max(1, Math.ceil(total / pageSize));
}

export function clampPage(page, total, pageSize) {
  const max = pageCount(total, pageSize);
  return Math.min(Math.max(1, page), max);
}

export function pageSlice(items, page, pageSize) {
  const current = clampPage(page, items.length, pageSize);
  const start = (current - 1) * pageSize;
  return {
    current,
    totalPages: pageCount(items.length, pageSize),
    items: items.slice(start, start + pageSize),
  };
}

export function paginationBar({ page, total, pageSize, onPage, labels }) {
  const current = clampPage(page, total, pageSize);
  const totalPages = pageCount(total, pageSize);
  const status = (labels.status || '{page} / {pages} · {total}')
    .replace('{page}', String(current))
    .replace('{pages}', String(totalPages))
    .replace('{total}', String(total));

  const start = Math.max(1, Math.min(current - 2, totalPages - 4));
  const end = Math.min(totalPages, start + 4);
  const pageButtons = [];
  for (let item = start; item <= end; item += 1) {
    pageButtons.push(el('button', {
      type: 'button',
      class: `btn btn-secondary btn-sm page-number${item === current ? ' active' : ''}`,
      ariaCurrent: item === current ? 'page' : null,
      onclick: () => onPage(item),
    }, String(item)));
  }

  return el('div', { class: 'pager-bar' },
    el('span', { class: 'pager-info' }, status),
    el('div', { class: 'pager-actions' },
      el('button', {
        type: 'button',
        class: 'btn btn-secondary btn-sm page-btn',
        disabled: current <= 1,
        onclick: () => onPage(current - 1),
      }, labels.prev),
      pageButtons,
      el('button', {
        type: 'button',
        class: 'btn btn-secondary btn-sm page-btn',
        disabled: current >= totalPages,
        onclick: () => onPage(current + 1),
      }, labels.next),
    ),
  );
}

import { el } from './dom.js';

export function button(label, { variant = 'secondary', size = '', onClick, type = 'button', disabled = false } = {}) {
  return el('button', {
    type,
    class: ['btn', `btn-${variant}`, size ? `btn-${size}` : ''].filter(Boolean).join(' '),
    disabled,
    onclick: onClick,
  }, label);
}

export function linkButton(label, href, { variant = 'secondary', size = '', download = '', target = '' } = {}) {
  const attrs = {
    class: ['btn', `btn-${variant}`, size ? `btn-${size}` : ''].filter(Boolean).join(' '),
    href,
  };
  if (download) attrs.download = download;
  if (target) attrs.target = target;
  if (target === '_blank') attrs.rel = 'noopener noreferrer';
  return el('a', attrs, label);
}

export function actions(...children) {
  return el('div', { class: 'action-row' }, children);
}

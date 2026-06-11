import { button, actions } from './buttons.js';
import { el } from './dom.js';

export function noticeModal({ title, message, actionLabel, tone = '' }) {
  const overlay = el('div', { class: 'modal-overlay' });
  const close = () => overlay.remove();
  overlay.appendChild(el('div', {
    class: ['modal', tone ? `modal-${tone}` : ''].filter(Boolean).join(' '),
    role: 'dialog',
    ariaModal: 'true',
  },
    el('h2', {}, title),
    el('p', {}, message),
    actions(button(actionLabel, { variant: 'primary', onClick: close })),
  ));
  document.body.appendChild(overlay);
  return overlay;
}

export function confirmModal({ title, message, confirmLabel, cancelLabel, danger = false, onConfirm }) {
  const overlay = el('div', { class: 'modal-overlay' });
  const close = () => overlay.remove();
  const confirm = button(confirmLabel, {
    variant: danger ? 'danger' : 'primary',
    onClick: async () => {
      await onConfirm?.();
      close();
    },
  });
  overlay.appendChild(el('div', { class: 'modal', role: 'dialog', ariaModal: 'true' },
    el('h2', {}, title),
    el('p', {}, message),
    actions(
      button(cancelLabel, { onClick: close }),
      confirm,
    ),
  ));
  document.body.appendChild(overlay);
  return overlay;
}

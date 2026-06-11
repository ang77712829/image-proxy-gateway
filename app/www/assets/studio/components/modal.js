import { button, actions } from './buttons.js';
import { el } from './dom.js';

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

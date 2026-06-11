let container;

function ensure() {
  if (!container) container = document.getElementById('toast-container');
  return container;
}

export function toast(message, type = 'info') {
  const node = document.createElement('div');
  node.className = `toast toast-${type}`;
  node.textContent = message;
  ensure().appendChild(node);
  setTimeout(() => node.remove(), 4200);
}

export const showToast = toast;

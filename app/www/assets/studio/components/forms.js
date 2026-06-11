import { el } from './dom.js';

export function field(label, control, { help = '', className = '' } = {}) {
  return el('label', { class: ['field', className].filter(Boolean).join(' ') },
    el('span', { class: 'field-label' }, label),
    control,
    help ? el('span', { class: 'field-help' }, help) : null,
  );
}

export function input(attrs = {}) {
  const { class: className = '', ...rest } = attrs;
  return el('input', { ...rest, class: ['control', className].filter(Boolean).join(' ') });
}

export function textarea(attrs = {}) {
  const { class: className = '', ...rest } = attrs;
  return el('textarea', { ...rest, class: ['control', className].filter(Boolean).join(' ') });
}

export function select(options, attrs = {}) {
  const { class: className = '', value, ...rest } = attrs;
  const node = el('select', { ...rest, class: ['control', className].filter(Boolean).join(' ') });
  options.forEach((option) => {
    node.appendChild(el('option', {
      value: option.value,
      selected: option.selected,
      disabled: option.disabled,
    }, option.label));
  });
  if (value !== undefined) node.value = value;
  return node;
}

export function toggle(label, attrs = {}) {
  const control = input({ type: 'checkbox', ...attrs });
  return el('label', { class: 'toggle' },
    control,
    el('span', { class: 'toggle-track' }),
    el('span', { class: 'toggle-label' }, label),
  );
}

export function segmented(options, current, onChange) {
  const group = el('div', { class: 'segmented', role: 'tablist' });
  options.forEach((option) => {
    const item = el('button', {
      type: 'button',
      class: option.value === current ? 'active' : '',
      onclick: () => onChange(option.value),
    }, option.label);
    group.appendChild(item);
  });
  return group;
}

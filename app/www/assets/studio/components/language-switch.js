import { t, getLanguage, setLanguage, supportedLanguages } from '../i18n.js';
import { el } from './dom.js';

const LANGUAGE_META = {
  'zh-CN': { code: 'CN', label: '中文' },
  'en-US': { code: 'EN', label: 'English' },
};

export function languageSwitch() {
  const current = getLanguage();
  const currentMeta = LANGUAGE_META[current] || { code: current, label: current };
  const menu = el('div', {
    class: 'language-menu',
    hidden: true,
    role: 'menu',
    onclick: (event) => event.stopPropagation(),
  });
  const trigger = el('button', {
    type: 'button',
    class: 'top-action top-action-language-trigger',
    title: t('topbar.language'),
    ariaLabel: t('topbar.language'),
    ariaExpanded: 'false',
    onclick: (event) => {
      event.stopPropagation();
      const nextOpen = menu.hidden;
      menu.hidden = !nextOpen;
      trigger.setAttribute('aria-expanded', String(nextOpen));
    },
  },
    el('span', { class: 'top-action-globe', ariaHidden: true }),
    el('span', { class: 'top-action-label' }, currentMeta.code),
  );

  supportedLanguages.forEach((lang) => {
    const meta = LANGUAGE_META[lang] || { code: lang, label: lang };
    menu.appendChild(el('button', {
      type: 'button',
      class: `language-option${lang === current ? ' active' : ''}`,
      role: 'menuitem',
      onclick: () => {
        if (lang !== current) {
          setLanguage(lang);
          location.reload();
          return;
        }
        menu.hidden = true;
        trigger.setAttribute('aria-expanded', 'false');
      },
    },
      el('span', { class: 'language-option-code' }, meta.code),
      el('span', {}, meta.label),
    ));
  });

  document.addEventListener('click', () => {
    menu.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      menu.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
    }
  });

  return el('div', { class: 'language-switch' }, trigger, menu);
}

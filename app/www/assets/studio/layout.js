import { logout, getSession } from './auth.js';
import { navigate } from './router.js';
import { t } from './i18n.js';
import { el } from './components/dom.js';
import { languageSwitch } from './components/language-switch.js';
import { showWipFeature } from './components/wip.js';
import { getTheme, toggleTheme } from './lib/theme.js';

const NAV = [
  { hash: '#/dashboard', key: 'nav.dashboard', group: 'studio' },
  { hash: '#/generate/image', key: 'nav.generateImage', group: 'create' },
  { hash: '#/generate/video', key: 'nav.generateVideo', group: 'create' },
  { hash: '#/jobs', key: 'nav.jobs', group: 'manage' },
  { hash: '#/assets', key: 'nav.assets', group: 'manage' },
  { hash: '#/providers', key: 'nav.providers', group: 'config' },
  { hash: '#/gateway-keys', key: 'nav.apiKeys', group: 'config' },
];

let shellRendered = false;

function topAction({ label, icon, onClick, title = '', className = '', wip = false }) {
  return el('button', {
    type: 'button',
    class: ['top-action', className].filter(Boolean).join(' '),
    title: title || label,
    ariaLabel: title || label,
    onclick: onClick,
  },
    icon ? el('span', { class: 'top-action-icon' }, icon) : null,
    el('span', { class: 'top-action-label' }, label),
    wip ? el('span', { class: 'top-wip-badge' }, 'WIP') : null,
  );
}

function renderNav() {
  const nav = document.querySelector('.sidebar-nav');
  if (!nav) return;
  nav.textContent = '';
  let lastGroup = '';
  NAV.forEach((item) => {
    if (item.group !== lastGroup) {
      nav.appendChild(el('p', { class: 'nav-group' }, t(`navGroup.${item.group}`)));
      lastGroup = item.group;
    }
    nav.appendChild(el('a', { class: 'nav-item', href: item.hash, dataset: { route: item.hash } },
      el('span', { class: 'nav-marker' }),
      el('span', { class: 'nav-label' }, t(item.key)),
    ));
  });
}

export function renderShell() {
  if (shellRendered) return;
  shellRendered = true;

  const sidebar = document.getElementById('sidebar');
  const topbar = document.getElementById('topbar');

  sidebar.textContent = '';
  sidebar.append(
    el('div', { class: 'sidebar-brand' },
      el('strong', {}, 'AngeMedia'),
      el('span', {}, 'Studio'),
    ),
    el('nav', { class: 'sidebar-nav', ariaLabel: 'Studio navigation' }),
    el('div', { class: 'sidebar-footer' },
      el('p', {}, t('shell.localMode')),
      el('span', { class: 'soft-pill' }, t('shell.selfHosted')),
    ),
  );
  renderNav();

  topbar.textContent = '';
  const themeButton = topAction({
    label: t('topbar.theme'),
    icon: 'Aa',
    title: getTheme() === 'dark' ? t('theme.toLight') : t('theme.toDark'),
    onClick: () => {
      const next = toggleTheme();
      const title = next === 'dark' ? t('theme.toLight') : t('theme.toDark');
      themeButton.title = title;
      themeButton.setAttribute('aria-label', title);
    },
  });

  const assistantButton = topAction({
    label: t('topbar.assistant'),
    icon: 'AI',
    title: t('topbar.assistantWip'),
    wip: true,
    onClick: () => showWipFeature({ title: t('wip.promptCopilotTitle') }),
  });

  const diagnosticsButton = topAction({
    label: t('topbar.diagnostics'),
    icon: 'DX',
    title: t('topbar.diagnosticsWip'),
    wip: true,
    onClick: () => navigate('#/diagnostics'),
  });

  const logoutButton = topAction({
    label: t('topbar.logout'),
    icon: 'OUT',
    onClick: () => logout(),
  });

  topbar.appendChild(el('div', { class: 'topbar-inner' },
    el('div', { class: 'brand' },
      el('div', { class: 'logo' }, 'Ange', el('em', {}, 'Media')),
      el('div', { class: 'brand-line' }),
      el('div', { class: 'title-block' },
        el('div', { class: 'eyebrow' }, 'ANGEMEDIA STUDIO'),
        el('h1', {}, t('topbar.studio')),
      ),
    ),
    el('div', { class: 'top-actions' },
      el('span', { class: 'top-action top-action-status', title: t('topbar.gatewayOnline') },
        el('span', { class: 'top-action-icon' }, 'ON'),
        el('span', { class: 'top-action-label' }, t('topbar.gatewayOnline')),
      ),
      assistantButton,
      diagnosticsButton,
      themeButton,
      languageSwitch(),
      logoutButton,
    ),
  ));

  updateActiveNav();
  window.addEventListener('hashchange', updateActiveNav);
}

export function setChromeVisible(visible) {
  const sidebar = document.getElementById('sidebar');
  const topbar = document.getElementById('topbar');
  if (sidebar) sidebar.style.display = visible ? '' : 'none';
  if (topbar) topbar.style.display = visible ? '' : 'none';
}

export function updateActiveNav() {
  const current = location.hash || '#/dashboard';
  document.querySelectorAll('.nav-item').forEach(a => {
    const route = a.getAttribute('href') || '';
    const active = route === current || (route !== '#/dashboard' && current.startsWith(`${route}/`));
    a.classList.toggle('active', active);
  });
}

export async function guard() {
  const s = await getSession();
  if (!s) {
    navigate('#/login');
    return false;
  }
  return true;
}

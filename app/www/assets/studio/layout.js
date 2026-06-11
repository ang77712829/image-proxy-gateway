import { logout, getSession } from './auth.js';
import { navigate } from './router.js';
import { t, getLanguage, setLanguage, supportedLanguages } from './i18n.js';
import { el } from './components/dom.js';

const NAV = [
  { hash: '#/dashboard', key: 'nav.dashboard', group: 'studio' },
  { hash: '#/generate/image', key: 'nav.generateImage', group: 'create' },
  { hash: '#/jobs', key: 'nav.jobs', group: 'manage' },
  { hash: '#/assets', key: 'nav.assets', group: 'manage' },
  { hash: '#/providers', key: 'nav.providers', group: 'config' },
  { hash: '#/gateway-keys', key: 'nav.apiKeys', group: 'config' },
];

let shellRendered = false;

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

  const langOptions = supportedLanguages.map(lang =>
    `<option value="${lang}">${lang}</option>`
  ).join('');

  topbar.innerHTML = `
    <div class="topbar-left">
      <span class="topbar-kicker">ANGEMEDIA STUDIO</span>
      <span class="topbar-title">${t('topbar.studio')}</span>
    </div>
    <div class="topbar-right">
      <span class="status-pill"><span></span>${t('topbar.gatewayOnline')}</span>
      <select id="studio-lang" class="compact-select" aria-label="${t('topbar.language')}">
        ${langOptions}
      </select>
      <button class="btn btn-sm" id="logout-btn">${t('topbar.logout')}</button>
    </div>
  `;

  const langSelect = document.getElementById('studio-lang');
  langSelect.value = getLanguage();
  langSelect.addEventListener('change', (e) => {
    setLanguage(e.target.value);
    location.reload();
  });

  document.getElementById('logout-btn').addEventListener('click', () => logout());
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

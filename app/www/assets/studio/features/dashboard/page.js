import { api } from '../../api.js';
import { t } from '../../i18n.js';
import { button } from '../../components/buttons.js';
import { el, mount } from '../../components/dom.js';
import { pageHeader, panel, metricCard, metaGrid } from '../../components/page.js';
import { badge, statusBadge } from '../../components/badges.js';
import { emptyState, errorState, loadingState } from '../../components/states.js';
import { formatDate, shortId, truncateText } from '../../lib/format.js';
import { safeText } from '../../lib/security.js';
import { navigate } from '../../router.js';

async function fetchHealth() {
  const res = await fetch('/health', { credentials: 'include' });
  if (!res.ok) throw new Error('health failed');
  return res.json();
}

function dataArray(result) {
  return Array.isArray(result?.data) ? result.data : [];
}

function recentJobCard(job) {
  return el('article', { class: `job-card ${job.status === 'failed' ? 'failed' : ''}` },
    el('div', { class: 'job-card-header' },
      el('div', {},
        el('p', { class: 'card-title' }, shortId(job.id)),
        el('p', { class: 'card-subtitle' }, truncateText(job.prompt || '-', 88)),
      ),
      statusBadge(job.status, t(`jobs.${job.status}`)),
    ),
    metaGrid([
      { label: t('jobs.kind'), value: t(`jobs.${job.kind}`) },
      { label: t('jobs.provider'), value: job.provider || '-' },
      { label: t('jobs.model'), value: job.model || '-' },
      { label: t('jobs.created'), value: formatDate(job.created_at) },
    ]),
  );
}

function providerSummaryCard(provider) {
  return el('article', { class: 'provider-row' },
    el('span', { class: 'provider-logo' }, safeText(provider.name || provider.id || '?', 1).slice(0, 1).toUpperCase()),
    el('div', { class: 'truncate' },
      el('b', { class: 'truncate' }, safeText(provider.name || provider.id || '-', 80)),
      el('p', { class: 'card-subtitle' }, safeText(provider.default_model || provider.provider_type || '-', 96)),
    ),
    el('div', { class: 'action-row' },
      provider.enabled ? badge(t('providers.enabled'), 'success') : badge(t('providers.disabled'), 'muted'),
      provider.api_key_configured ? badge(t('providers.configured'), 'success') : badge(t('providers.notConfigured'), 'warning'),
    ),
  );
}

function queuePanel(jobs) {
  const counts = jobs.reduce((acc, job) => {
    acc[job.status] = (acc[job.status] || 0) + 1;
    return acc;
  }, {});
  return panel({ title: t('dashboard.queue') },
    el('div', { class: 'queue-box' },
      el('div', { class: 'queue-cell' }, el('span', {}, t('jobs.queued')), el('b', {}, String(counts.queued || 0))),
      el('div', { class: 'queue-cell' }, el('span', {}, t('jobs.running')), el('b', {}, String(counts.running || 0))),
      el('div', { class: 'queue-cell' }, el('span', {}, t('jobs.succeeded')), el('b', {}, String(counts.succeeded || 0))),
      el('div', { class: 'queue-cell' }, el('span', {}, t('jobs.failed')), el('b', {}, String(counts.failed || 0))),
    ),
  );
}

function storageWipPanel() {
  return panel({ title: t('dashboard.storage'), actions: [badge('WIP', 'warning')] },
    el('div', { class: 'disk-card' },
      el('div', { class: 'disk-ring disk-ring-wip' }, el('strong', {}, t('dashboard.notConnected'))),
      el('div', {},
        el('div', { class: 'eyebrow' }, 'DISK USAGE'),
        el('p', { class: 'card-subtitle' }, t('dashboard.storageWip')),
      ),
    ),
  );
}

function recentFailuresPanel(jobs) {
  const failures = jobs.filter((job) => job.status === 'failed').slice(0, 3);
  return panel({
    title: t('dashboard.recentFailures'),
    actions: [button(t('common.viewMore'), { size: 'sm', onClick: () => navigate('#/jobs') })],
  },
    el('div', { class: 'panel-body error-list' },
      failures.length ? failures.map((job) => el('article', { class: 'error-row' },
        el('span', {}, formatDate(job.created_at)),
        el('span', { class: 'truncate' }, safeText(job.human_hint || job.error_message || job.prompt || job.id, 120)),
        badge(job.error_category || t('jobs.failed'), 'danger'),
      )) : emptyState(t('dashboard.noRecentFailures')),
    ),
  );
}

export async function render() {
  const content = document.getElementById('content');
  mount(content,
    pageHeader({
      kicker: t('dashboard.kicker'),
      title: t('dashboard.title'),
      subtitle: t('dashboard.subtitle'),
      actions: [
        button(t('dashboard.generateImageCta'), { variant: 'primary', onClick: () => navigate('#/generate/image') }),
        button(t('dashboard.reviewAssets'), { onClick: () => navigate('#/assets') }),
      ],
    }),
    loadingState(t('common.loading')),
  );

  try {
    const [health, session, jobsResult, assetsResult, providersResult, keysResult] = await Promise.all([
      fetchHealth().catch(() => ({ status: 'error' })),
      api.get('/admin/session').catch(() => ({ authenticated: false })),
      api.get('/jobs?limit=8&offset=0').catch(() => ({ data: [] })),
      api.get('/assets?limit=100&offset=0').catch(() => ({ data: [] })),
      api.get('/admin/providers').catch(() => ({ data: [] })),
      api.get('/admin/gateway-keys').catch(() => ({ data: [] })),
    ]);

    const jobs = dataArray(jobsResult);
    const assets = dataArray(assetsResult);
    const providers = dataArray(providersResult);
    const keys = dataArray(keysResult).filter((item) => !item.revoked_at);
    const failedCount = jobs.filter((job) => job.status === 'failed').length;

    mount(content,
      pageHeader({
        kicker: t('dashboard.kicker'),
        title: t('dashboard.title'),
        subtitle: t('dashboard.subtitle'),
        actions: [
          button(t('dashboard.generateImageCta'), { variant: 'primary', onClick: () => navigate('#/generate/image') }),
          button(t('dashboard.reviewAssets'), { onClick: () => navigate('#/assets') }),
        ],
      }),
      el('div', { class: 'metric-grid' },
        metricCard({ label: t('dashboard.health'), value: health.status === 'ok' ? t('dashboard.ready') : t('dashboard.notConnected'), meta: t('topbar.gatewayOnline'), tone: 'teal', icon: '◎' }),
        metricCard({ label: t('dashboard.session'), value: session.authenticated ? t('dashboard.signedIn') : t('dashboard.notAuthenticated'), meta: session.username || '-', tone: 'blue', icon: '◇' }),
        metricCard({ label: t('dashboard.assets'), value: String(assets.length), meta: t('assets.title'), tone: 'violet', icon: '▧' }),
        metricCard({ label: t('dashboard.jobs'), value: String(jobs.length), meta: `${failedCount} ${t('dashboard.failedJobs')}`, tone: 'gold', icon: '▤' }),
        metricCard({ label: t('dashboard.providers'), value: String(providers.length), meta: `${keys.length} ${t('dashboard.activeKeys')}`, tone: 'teal', icon: '✣' }),
      ),
      el('div', { class: 'dashboard-grid' },
        panel({ title: t('dashboard.recentJobs') },
          el('div', { class: 'panel-body' },
            jobs.length ? el('div', { class: 'recent-strip' }, jobs.slice(0, 4).map(recentJobCard)) :
              emptyState(t('jobs.empty')),
          ),
        ),
        el('aside', { class: 'side-stack' },
          queuePanel(jobs),
          storageWipPanel(),
        ),
      ),
      el('div', { class: 'dashboard-grid dashboard-grid-bottom' },
        panel({
          title: t('dashboard.providerSummary'),
          actions: [button(t('common.viewMore'), { size: 'sm', onClick: () => navigate('#/providers') })],
        },
          el('div', { class: 'panel-body provider-summary' },
            providers.length ? providers.slice(0, 4).map(providerSummaryCard) : emptyState(t('dashboard.noProviders')),
          ),
        ),
        recentFailuresPanel(jobs),
      ),
    );
  } catch (_) {
    mount(content,
      pageHeader({ kicker: t('dashboard.kicker'), title: t('dashboard.title'), subtitle: t('dashboard.subtitle') }),
      errorState(t('dashboard.loadFailed')),
    );
  }
}

import { api } from '../../api.js';
import { t } from '../../i18n.js';
import { button } from '../../components/buttons.js';
import { el, mount } from '../../components/dom.js';
import { pageHeader, panel, metricCard, metaGrid } from '../../components/page.js';
import { statusBadge } from '../../components/badges.js';
import { emptyState, errorState, loadingState } from '../../components/states.js';
import { formatDate, shortId, truncateText } from '../../lib/format.js';
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
        metricCard({ label: t('dashboard.health'), value: health.status === 'ok' ? t('dashboard.ready') : 'Error', meta: t('topbar.gatewayOnline'), tone: 'teal' }),
        metricCard({ label: t('dashboard.session'), value: session.authenticated ? t('dashboard.signedIn') : t('dashboard.notAuthenticated'), meta: session.username || '-', tone: 'blue' }),
        metricCard({ label: t('dashboard.assets'), value: String(assets.length), meta: t('assets.title'), tone: 'violet' }),
        metricCard({ label: t('dashboard.jobs'), value: String(jobs.length), meta: `${providers.length} ${t('dashboard.providers')} / ${keys.length} ${t('dashboard.apiKeys')}`, tone: 'gold' }),
      ),
      panel({ title: t('dashboard.recentJobs') },
        el('div', { class: 'panel-body' },
          jobs.length ? el('div', { class: 'recent-strip' }, jobs.slice(0, 4).map(recentJobCard)) :
            emptyState(t('jobs.empty')),
        ),
      ),
    );
  } catch (_) {
    mount(content,
      pageHeader({ kicker: t('dashboard.kicker'), title: t('dashboard.title'), subtitle: t('dashboard.subtitle') }),
      errorState(t('dashboard.loadFailed')),
    );
  }
}

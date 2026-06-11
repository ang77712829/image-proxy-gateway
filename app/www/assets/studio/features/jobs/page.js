import { api } from '../../api.js';
import { t } from '../../i18n.js';
import { button } from '../../components/buttons.js';
import { badge, statusBadge } from '../../components/badges.js';
import { el, mount } from '../../components/dom.js';
import { segmented } from '../../components/forms.js';
import { pageHeader, panel, metricCard, metaGrid } from '../../components/page.js';
import { emptyState, errorState, loadingState } from '../../components/states.js';
import { formatDate, formatDuration, shortId, truncateText } from '../../lib/format.js';
import { safeText } from '../../lib/security.js';
import { navigate } from '../../router.js';

let currentStatus = '';
let allJobs = [];

const STATUS_OPTIONS = [
  { value: '', key: 'jobs.all' },
  { value: 'queued', key: 'jobs.queued' },
  { value: 'running', key: 'jobs.running' },
  { value: 'succeeded', key: 'jobs.succeeded' },
  { value: 'failed', key: 'jobs.failed' },
  { value: 'canceled', key: 'jobs.canceled' },
];

function dataArray(result) {
  return Array.isArray(result?.data) ? result.data : [];
}

function kindLabel(job) {
  if (job.kind === 'image') return t('jobs.image');
  if (job.kind === 'video') return t('jobs.video');
  return job.kind || t('jobs.unknown');
}

function diagnosticBlock(job) {
  if (job.status !== 'failed' && !job.human_hint && !job.error_category) return null;
  return el('div', { class: 'job-diagnostics' },
    job.human_hint ? el('p', { class: 'job-hint' }, safeText(job.human_hint, 180)) : null,
    el('div', { class: 'action-row' },
      job.error_category ? badge(job.error_category, 'danger') : null,
      job.retryable === true ? badge(t('jobs.retryable'), 'warning') : null,
      job.retryable === false ? badge(t('jobs.notRetryable'), 'muted') : null,
      job.gateway_stage ? badge(job.gateway_stage, 'info') : null,
    ),
    job.error_message ? el('p', { class: 'job-safe-message' }, `${t('jobs.safeMessage')}: ${safeText(job.error_message, 160)}`) : null,
  );
}

function jobCard(job) {
  return el('article', { class: `job-card ${job.status === 'failed' ? 'failed' : ''}` },
    el('div', { class: 'job-card-header' },
      el('div', {},
        el('p', { class: 'card-title' }, `${kindLabel(job)} · ${shortId(job.id)}`),
        el('p', { class: 'card-subtitle' }, truncateText(job.prompt || '-', 120)),
      ),
      statusBadge(job.status, t(`jobs.${job.status}`)),
    ),
    metaGrid([
      { label: t('jobs.provider'), value: job.provider || '-' },
      { label: t('jobs.model'), value: job.model || '-' },
      { label: t('jobs.created'), value: formatDate(job.created_at) },
      { label: t('jobs.duration'), value: formatDuration(job.duration_ms) },
      { label: t('jobs.gatewayStage'), value: job.gateway_stage || '' },
    ]),
    diagnosticBlock(job),
    el('div', { class: 'action-row' },
      button(t('jobs.detail'), { size: 'sm', onClick: () => navigate(`#/jobs/${encodeURIComponent(job.id)}`) }),
    ),
  );
}

function renderJobs(content, reload) {
  const filtered = currentStatus ? allJobs.filter((job) => job.status === currentStatus) : allJobs;
  const counts = allJobs.reduce((acc, job) => {
    acc[job.status] = (acc[job.status] || 0) + 1;
    return acc;
  }, {});

  mount(content,
    pageHeader({
      kicker: t('jobs.kicker'),
      title: t('jobs.title'),
      subtitle: t('jobs.subtitle'),
      actions: [button(t('common.refresh'), { onClick: reload })],
    }),
    el('div', { class: 'metric-grid' },
      metricCard({ label: t('jobs.all'), value: String(allJobs.length), meta: t('jobs.title'), tone: 'teal' }),
      metricCard({ label: t('jobs.running'), value: String(counts.running || 0), meta: t('jobs.queued'), tone: 'blue' }),
      metricCard({ label: t('jobs.succeeded'), value: String(counts.succeeded || 0), meta: t('jobs.duration'), tone: 'violet' }),
      metricCard({ label: t('jobs.failed'), value: String(counts.failed || 0), meta: t('jobs.humanHint'), tone: 'gold' }),
    ),
    panel({},
      el('div', { class: 'jobs-toolbar' },
        segmented(STATUS_OPTIONS.map((item) => ({ value: item.value, label: t(item.key) })), currentStatus, (next) => {
          currentStatus = next;
          renderJobs(content, reload);
        }),
        badge(`${filtered.length} / ${allJobs.length}`, 'muted'),
      ),
      el('div', { class: 'jobs-content' },
        filtered.length ? el('div', { class: 'job-list' }, filtered.map(jobCard)) :
          emptyState(t('jobs.empty')),
      ),
    ),
  );
}

export async function render() {
  const content = document.getElementById('content');

  async function reload() {
    mount(content, loadingState(t('jobs.loading')));
    try {
      const result = await api.get('/jobs?limit=100&offset=0');
      allJobs = dataArray(result);
      renderJobs(content, reload);
    } catch (_) {
      mount(content,
        pageHeader({ kicker: t('jobs.kicker'), title: t('jobs.title'), subtitle: t('jobs.subtitle') }),
        errorState(t('jobs.error')),
      );
    }
  }

  await reload();
}

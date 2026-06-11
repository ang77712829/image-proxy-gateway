import { api } from '../../api.js';
import { t } from '../../i18n.js';
import { button } from '../../components/buttons.js';
import { badge, statusBadge } from '../../components/badges.js';
import { el, mount } from '../../components/dom.js';
import { segmented } from '../../components/forms.js';
import { clampPage, pageSlice, paginationBar } from '../../components/pagination.js';
import { pageHeader, panel, metricCard, metaGrid } from '../../components/page.js';
import { emptyState, errorState, loadingState } from '../../components/states.js';
import { formatDate, formatDuration, shortId, truncateText } from '../../lib/format.js';
import { safeText } from '../../lib/security.js';

let currentStatus = '';
let allJobs = [];
let jobPage = 1;

const JOB_PAGE_SIZE = 6;

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

function pagerLabels() {
  return {
    prev: t('common.prev'),
    next: t('common.next'),
    status: t('common.pageStatus'),
  };
}

function kindLabel(job) {
  if (job.kind === 'image') return t('jobs.image');
  if (job.kind === 'video') return t('jobs.video');
  return job.kind || t('jobs.unknown');
}

function diagnosticBlock(job) {
  if (job.status !== 'failed' && !job.human_hint && !job.error_category) return null;
  const details = el('p', {
    class: 'job-safe-message job-detail-line',
    hidden: true,
  }, job.error_message ? `${t('jobs.safeMessage')}: ${safeText(job.error_message, 180)}` : t('common.none'));
  const toggle = button(t('jobs.showDiagnostics'), {
    size: 'sm',
    onClick: () => {
      details.hidden = !details.hidden;
      toggle.textContent = details.hidden ? t('jobs.showDiagnostics') : t('jobs.hideDiagnostics');
    },
  });

  return el('div', { class: 'job-diagnostics' },
    el('div', { class: 'job-diagnostic-strip' }, toggle),
    details,
  );
}

function diagnosticSummary(job) {
  if (job.status !== 'failed' && !job.human_hint && !job.error_category) return null;
  return el('div', { class: 'job-diagnostic-summary' },
    job.human_hint ? el('span', { class: 'job-hint truncate' }, safeText(job.human_hint, 120)) : null,
    el('div', { class: 'action-row' },
      job.error_category ? badge(job.error_category, 'danger') : null,
      job.retryable === true ? badge(t('jobs.retryable'), 'warning') : null,
      job.retryable === false ? badge(t('jobs.notRetryable'), 'muted') : null,
      job.gateway_stage ? badge(job.gateway_stage, 'info') : null,
    ),
  );
}

function jobCard(job) {
  return el('article', { class: `job-card job-row ${job.status === 'failed' ? 'failed' : ''}` },
    el('div', { class: 'job-main' },
      el('p', { class: 'card-title' }, `${kindLabel(job)} · ${shortId(job.id)}`),
      el('p', { class: 'card-subtitle' }, formatDate(job.created_at)),
      el('p', { class: 'prompt' }, truncateText(safeText(job.prompt || '-', 220), 140)),
      diagnosticSummary(job),
    ),
    el('div', { class: 'kv-grid' },
      el('div', { class: 'kv' },
        el('b', {}, t('jobs.status')),
        statusBadge(job.status, t(`jobs.${job.status}`)),
      ),
      el('div', { class: 'kv' },
        el('b', {}, t('jobs.provider')),
        el('span', {}, safeText(job.provider || '-', 80)),
      ),
      el('div', { class: 'kv' },
        el('b', {}, t('jobs.model')),
        el('span', {}, safeText(job.model || '-', 80)),
      ),
      el('div', { class: 'kv' },
        el('b', {}, t('jobs.gatewayStage')),
        el('span', {}, safeText(job.gateway_stage || '-', 80)),
      ),
      el('div', { class: 'kv' },
        el('b', {}, t('jobs.retryable')),
        el('span', {}, job.retryable === true ? t('jobs.retryable') : job.retryable === false ? t('jobs.notRetryable') : '-'),
      ),
      el('div', { class: 'kv' },
        el('b', {}, t('jobs.errorCategory')),
        el('span', {}, safeText(job.error_category || '-', 80)),
      ),
    ),
    el('div', { class: 'job-side' },
      metaGrid([{ label: t('jobs.duration'), value: formatDuration(job.duration_ms) }]),
      diagnosticBlock(job),
    ),
  );
}

function renderJobs(content, reload) {
  const filtered = currentStatus ? allJobs.filter((job) => job.status === currentStatus) : allJobs;
  const paged = pageSlice(filtered, jobPage, JOB_PAGE_SIZE);
  jobPage = paged.current;
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
      metricCard({ label: t('jobs.all'), value: String(allJobs.length), meta: t('jobs.title'), tone: 'teal', icon: '▤' }),
      metricCard({ label: t('jobs.running'), value: String(counts.running || 0), meta: t('jobs.queued'), tone: 'blue', icon: '◌' }),
      metricCard({ label: t('jobs.succeeded'), value: String(counts.succeeded || 0), meta: t('jobs.duration'), tone: 'violet', icon: '✓' }),
      metricCard({ label: t('jobs.failed'), value: String(counts.failed || 0), meta: t('jobs.humanHint'), tone: 'gold', icon: '!' }),
    ),
    panel({},
      el('div', { class: 'jobs-toolbar' },
        segmented(STATUS_OPTIONS.map((item) => ({ value: item.value, label: t(item.key) })), currentStatus, (next) => {
          currentStatus = next;
          jobPage = 1;
          renderJobs(content, reload);
        }),
        badge(`${filtered.length} / ${allJobs.length}`, 'muted'),
      ),
      el('div', { class: 'jobs-content' },
        filtered.length ? el('div', { class: 'job-list bounded-list' }, paged.items.map(jobCard)) :
          emptyState(t('jobs.empty')),
      ),
      paginationBar({
        page: jobPage,
        total: filtered.length,
        pageSize: JOB_PAGE_SIZE,
        labels: pagerLabels(),
        onPage: (page) => {
          jobPage = page;
          renderJobs(content, reload);
        },
      }),
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
      const filtered = currentStatus ? allJobs.filter((job) => job.status === currentStatus) : allJobs;
      jobPage = clampPage(jobPage, filtered.length, JOB_PAGE_SIZE);
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

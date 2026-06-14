import { api } from '../../api.js';
import { t } from '../../i18n.js';
import { statusBadge } from '../../components/badges.js';
import { el } from '../../components/dom.js';
import { metaGrid, panel } from '../../components/page.js';
import { emptyState } from '../../components/states.js';
import { formatDate, shortId, truncateText } from '../../lib/format.js';
import { safeText } from '../../lib/security.js';

function recentJobCard(job) {
  return el('article', { class: `job-card ${job.status === 'failed' ? 'failed' : ''}` },
    el('div', { class: 'job-card-header' },
      el('div', {},
        el('p', { class: 'card-title' }, shortId(job.id)),
        el('p', { class: 'card-subtitle' }, truncateText(safeText(job.prompt || '-', 160), 72)),
      ),
      statusBadge(job.status, t(`jobs.${job.status}`)),
    ),
    metaGrid([
      { label: t('jobs.provider'), value: safeText(job.provider || '-', 80) },
      { label: t('jobs.model'), value: safeText(job.model || '-', 80) },
      { label: t('jobs.created'), value: formatDate(job.created_at) },
    ]),
  );
}

export async function loadRecentImageJobs() {
  const result = await api.get('/jobs?kind=image&limit=4&offset=0');
  return Array.isArray(result?.data) ? result.data : [];
}

export function recentImagesPanel(recentJobs) {
  return panel({ title: t('generateImage.recentImages') },
    el('div', { class: 'panel-body' },
      recentJobs.length ? el('div', { class: 'recent-strip' }, recentJobs.map(recentJobCard)) :
        emptyState(t('generateImage.noRecentJobs')),
    ),
  );
}

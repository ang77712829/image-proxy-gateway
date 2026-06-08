import { api } from '../api.js';
import { t } from '../i18n.js';

function truncate(str, maxLen) {
  if (!str) return '';
  return str.length > maxLen ? str.substring(0, maxLen) + '...' : str;
}

function formatDuration(ms) {
  if (!ms && ms !== 0) return '-';
  return `${ms}ms`;
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

export async function render() {
  const content = document.getElementById('content');
  content.innerHTML = '';

  const card = document.createElement('div');
  card.className = 'card';

  const h2 = document.createElement('h2');
  h2.textContent = t('jobs.title');
  card.appendChild(h2);

  const loading = document.createElement('p');
  loading.textContent = t('jobs.loading');
  loading.className = 'text-muted';
  card.appendChild(loading);

  content.appendChild(card);

  try {
    const result = await api.get('/jobs?limit=20&offset=0');
    loading.remove();

    const jobs = Array.isArray(result?.data) ? result.data : [];

    if (jobs.length === 0) {
      const empty = document.createElement('p');
      empty.textContent = t('jobs.empty');
      empty.className = 'text-muted';
      card.appendChild(empty);
      return;
    }

    const table = document.createElement('table');
    table.className = 'data-table';

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    const headers = [
      t('jobs.id'),
      t('jobs.kind'),
      t('jobs.status'),
      t('jobs.created'),
      t('jobs.duration'),
      t('jobs.provider'),
      t('jobs.model'),
      t('jobs.errorCode'),
    ];
    headers.forEach(text => {
      const th = document.createElement('th');
      th.textContent = text;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    jobs.forEach(job => {
      const row = document.createElement('tr');

      // ID (前8位)
      const tdId = document.createElement('td');
      tdId.textContent = job.id ? job.id.substring(0, 8) : '-';
      row.appendChild(tdId);

      // Kind
      const tdKind = document.createElement('td');
      tdKind.textContent = job.kind === 'image' ? t('jobs.image') :
                          job.kind === 'video' ? t('jobs.video') :
                          job.kind || t('jobs.unknown');
      row.appendChild(tdKind);

      // Status
      const tdStatus = document.createElement('td');
      const statusKey = `jobs.${job.status}`;
      tdStatus.textContent = t(statusKey) !== statusKey ? t(statusKey) : job.status || '-';
      row.appendChild(tdStatus);

      // Created
      const tdCreated = document.createElement('td');
      tdCreated.textContent = formatDate(job.created_at);
      row.appendChild(tdCreated);

      // Duration
      const tdDuration = document.createElement('td');
      tdDuration.textContent = formatDuration(job.duration_ms);
      row.appendChild(tdDuration);

      // Provider
      const tdProvider = document.createElement('td');
      tdProvider.textContent = job.provider || '-';
      row.appendChild(tdProvider);

      // Model
      const tdModel = document.createElement('td');
      tdModel.textContent = job.model || '-';
      row.appendChild(tdModel);

      // Error Code
      const tdError = document.createElement('td');
      tdError.textContent = job.error_code || '-';
      if (job.error_code) tdError.className = 'text-danger';
      row.appendChild(tdError);

      tbody.appendChild(row);
    });

    table.appendChild(tbody);
    card.appendChild(table);

    // 可选：显示脱敏错误消息（截断到 120 字符）
    const errorJobs = jobs.filter(j => j.error_message);
    if (errorJobs.length > 0) {
      const errorSection = document.createElement('div');
      errorSection.className = 'meta-row error-summary';

      const errorTitle = document.createElement('p');
      errorTitle.textContent = `${t('jobs.error')}:`;
      errorTitle.className = 'meta-title';
      errorSection.appendChild(errorTitle);

      errorJobs.slice(0, 3).forEach(job => {
        const errorP = document.createElement('p');
        // 不展示完整响应，只展示截断的错误消息
        errorP.textContent = `[${job.id?.substring(0, 8) || '-'}] ${truncate(job.error_message, 120)}`;
        errorP.className = 'error-summary-line';
        errorSection.appendChild(errorP);
      });

      card.appendChild(errorSection);
    }
  } catch (err) {
    loading.remove();
    const errorText = document.createElement('p');
    errorText.textContent = t('jobs.error');
    errorText.className = 'error-text';
    card.appendChild(errorText);
  }
}

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
  loading.style.color = '#888';
  card.appendChild(loading);

  content.appendChild(card);

  try {
    const result = await api.get('/jobs?limit=20&offset=0');
    loading.remove();

    const jobs = Array.isArray(result?.data) ? result.data : [];

    if (jobs.length === 0) {
      const empty = document.createElement('p');
      empty.textContent = t('jobs.empty');
      empty.style.color = '#888';
      card.appendChild(empty);
      return;
    }

    const table = document.createElement('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';

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
      th.style.textAlign = 'left';
      th.style.padding = '8px';
      th.style.borderBottom = '2px solid #ddd';
      th.style.fontWeight = '600';
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    jobs.forEach(job => {
      const row = document.createElement('tr');
      row.style.borderBottom = '1px solid #eee';

      // ID (前8位)
      const tdId = document.createElement('td');
      tdId.textContent = job.id ? job.id.substring(0, 8) : '-';
      tdId.style.padding = '8px';
      row.appendChild(tdId);

      // Kind
      const tdKind = document.createElement('td');
      tdKind.textContent = job.kind === 'image' ? t('jobs.image') :
                          job.kind === 'video' ? t('jobs.video') :
                          job.kind || t('jobs.unknown');
      tdKind.style.padding = '8px';
      row.appendChild(tdKind);

      // Status
      const tdStatus = document.createElement('td');
      const statusKey = `jobs.${job.status}`;
      tdStatus.textContent = t(statusKey) !== statusKey ? t(statusKey) : job.status || '-';
      tdStatus.style.padding = '8px';
      row.appendChild(tdStatus);

      // Created
      const tdCreated = document.createElement('td');
      tdCreated.textContent = formatDate(job.created_at);
      tdCreated.style.padding = '8px';
      row.appendChild(tdCreated);

      // Duration
      const tdDuration = document.createElement('td');
      tdDuration.textContent = formatDuration(job.duration_ms);
      tdDuration.style.padding = '8px';
      row.appendChild(tdDuration);

      // Provider
      const tdProvider = document.createElement('td');
      tdProvider.textContent = job.provider || '-';
      tdProvider.style.padding = '8px';
      row.appendChild(tdProvider);

      // Model
      const tdModel = document.createElement('td');
      tdModel.textContent = job.model || '-';
      tdModel.style.padding = '8px';
      row.appendChild(tdModel);

      // Error Code
      const tdError = document.createElement('td');
      tdError.textContent = job.error_code || '-';
      tdError.style.padding = '8px';
      tdError.style.color = job.error_code ? '#e74c3c' : 'inherit';
      row.appendChild(tdError);

      tbody.appendChild(row);
    });

    table.appendChild(tbody);
    card.appendChild(table);

    // 可选：显示脱敏错误消息（截断到 120 字符）
    const errorJobs = jobs.filter(j => j.error_message);
    if (errorJobs.length > 0) {
      const errorSection = document.createElement('div');
      errorSection.style.marginTop = '16px';
      errorSection.style.fontSize = '12px';
      errorSection.style.color = '#888';

      const errorTitle = document.createElement('p');
      errorTitle.textContent = `${t('jobs.error')}:`;
      errorTitle.style.fontWeight = '600';
      errorTitle.style.marginBottom = '4px';
      errorSection.appendChild(errorTitle);

      errorJobs.slice(0, 3).forEach(job => {
        const errorP = document.createElement('p');
        // 不展示完整响应，只展示截断的错误消息
        errorP.textContent = `[${job.id?.substring(0, 8) || '-'}] ${truncate(job.error_message, 120)}`;
        errorP.style.margin = '2px 0';
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

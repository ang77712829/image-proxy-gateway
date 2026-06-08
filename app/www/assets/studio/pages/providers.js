import { api } from '../api.js';
import { t } from '../i18n.js';

const FORBIDDEN_RESPONSE_FIELDS = [
  '_api_key',
  'key_hash',
  'secret',
  '_secret',
  'token',
  'access_token',
  'password',
];

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

function shortId(id) {
  if (!id) return '-';
  return String(id).substring(0, 8);
}

function hasForbiddenField(item) {
  if (!item || typeof item !== 'object') return false;
  return FORBIDDEN_RESPONSE_FIELDS.some(field =>
    Object.prototype.hasOwnProperty.call(item, field)
  );
}

function isProviderObject(item) {
  return Boolean(item && typeof item === 'object' && !Array.isArray(item));
}

function providerArrayFromResponse(result) {
  if (Array.isArray(result?.data)) return result.data;
  if (Array.isArray(result)) return result;
  return null;
}

function apiKeyConfigured(item) {
  return Boolean(item && Object.prototype.hasOwnProperty.call(item, 'api_key') && item.api_key);
}

function createTextCell(value) {
  const td = document.createElement('td');
  td.textContent = value || '-';
  return td;
}

function createBooleanCell(value, trueLabel, falseLabel) {
  const td = document.createElement('td');
  const badge = document.createElement('span');
  badge.className = value ? 'badge badge-success' : 'badge badge-pending';
  badge.textContent = value ? trueLabel : falseLabel;
  td.appendChild(badge);
  return td;
}

function renderTable(providers) {
  const table = document.createElement('table');
  table.className = 'data-table';

  const headers = [
    t('providers.id'),
    t('providers.name'),
    t('providers.type'),
    t('providers.enabled'),
    t('providers.apiKey'),
    t('providers.defaultModel'),
    t('providers.sortOrder'),
    t('providers.lastTestStatus'),
    t('providers.lastResponseMs'),
    t('providers.lastTestAt'),
    t('providers.created'),
    t('providers.updated'),
  ];

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  headers.forEach(text => {
    const th = document.createElement('th');
    th.textContent = text;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  providers.forEach(item => {
    const row = document.createElement('tr');
    row.appendChild(createTextCell(shortId(item.id)));
    row.appendChild(createTextCell(item.name));
    row.appendChild(createTextCell(item.provider_type));
    row.appendChild(createBooleanCell(Boolean(item.enabled), t('providers.enabledYes'), t('providers.enabledNo')));
    row.appendChild(createBooleanCell(apiKeyConfigured(item), t('providers.configured'), t('providers.notConfigured')));
    row.appendChild(createTextCell(item.default_model));
    row.appendChild(createTextCell(String(item.sort_order ?? '-')));
    row.appendChild(createTextCell(item.last_test_status));
    row.appendChild(createTextCell(item.last_response_ms ? String(item.last_response_ms) : '-'));
    row.appendChild(createTextCell(formatDate(item.last_test_at)));
    row.appendChild(createTextCell(formatDate(item.created_at)));
    row.appendChild(createTextCell(formatDate(item.updated_at)));
    tbody.appendChild(row);
  });
  table.appendChild(tbody);
  return table;
}

export async function render() {
  const content = document.getElementById('content');
  content.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'page-header';
  const heading = document.createElement('h1');
  heading.className = 'page-heading';
  heading.textContent = t('providers.title');
  const subtitle = document.createElement('p');
  subtitle.className = 'page-subtitle';
  subtitle.textContent = t('providers.subtitle');
  header.append(heading, subtitle);
  content.appendChild(header);

  const card = document.createElement('div');
  card.className = 'card section-card';
  const loading = document.createElement('p');
  loading.className = 'text-muted';
  loading.textContent = t('providers.loading');
  card.appendChild(loading);
  content.appendChild(card);

  try {
    const result = await api.get('/admin/providers');
    card.textContent = '';
    const providerItems = providerArrayFromResponse(result);
    if (!providerItems) {
      const errorText = document.createElement('p');
      errorText.className = 'error-text';
      errorText.textContent = t('providers.error');
      card.appendChild(errorText);
      return;
    }

    const providers = providerItems.filter(isProviderObject);

    if (providers.some(hasForbiddenField)) {
      const securityError = document.createElement('p');
      securityError.className = 'error-text';
      securityError.textContent = t('providers.securityError');
      card.appendChild(securityError);
      return;
    }

    if (providers.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'text-muted';
      empty.textContent = t('providers.empty');
      card.appendChild(empty);
      return;
    }

    card.appendChild(renderTable(providers));
  } catch (_) {
    card.textContent = '';
    const errorText = document.createElement('p');
    errorText.className = 'error-text';
    errorText.textContent = t('providers.error');
    card.appendChild(errorText);
  }
}

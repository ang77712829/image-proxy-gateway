import { api } from '../../api.js';
import { t } from '../../i18n.js';
import { button } from '../../components/buttons.js';
import { badge } from '../../components/badges.js';
import { el, mount } from '../../components/dom.js';
import { field, input, textarea, toggle } from '../../components/forms.js';
import { clampPage, pageSlice, paginationBar } from '../../components/pagination.js';
import { pageHeader, panel, metaGrid } from '../../components/page.js';
import { emptyState, errorState, loadingState } from '../../components/states.js';
import { toast } from '../../components/toast.js';
import { formatDate, shortId } from '../../lib/format.js';
import { safeText } from '../../lib/security.js';

const LIST_FORBIDDEN_FIELDS = ['key', 'key_hash'];
const CREATE_FORBIDDEN_FIELDS = ['key_hash'];
const REVOKE_FORBIDDEN_FIELDS = ['key', 'key_hash'];
const KEY_PAGE_SIZE = 5;

let showRevoked = false;
let keysCache = [];
let oneTimeSecret = null;
let keyPage = 1;

function hasForbiddenField(value, fields) {
  if (!value || typeof value !== 'object') return false;
  if (Array.isArray(value)) return value.some((item) => hasForbiddenField(item, fields));
  return Object.keys(value).some((key) => fields.includes(key)) ||
    Object.values(value).some((item) => hasForbiddenField(item, fields));
}

function dataArray(result) {
  return Array.isArray(result?.data) ? result.data : [];
}

function visibleKeys() {
  return keysCache.filter((item) => showRevoked || !item.revoked_at);
}

function keyStatus(item) {
  if (item.revoked_at) return badge(t('apiKeys.revoked'), 'danger');
  if (item.enabled) return badge(t('apiKeys.enabled'), 'success');
  return badge(t('apiKeys.disabled'), 'muted');
}

function pagerLabels() {
  return {
    prev: t('common.prev'),
    next: t('common.next'),
    status: t('common.pageStatus'),
  };
}

function renderSecretPanel(data, onDismiss) {
  const fullKey = String(data.key || '');
  const keyBox = textarea({ rows: 2, readOnly: true, value: fullKey, autocomplete: 'off' });
  return panel({ title: t('apiKeys.createdTitle'), subtitle: t('apiKeys.createdWarning'), className: 'secret-box' },
    el('div', { class: 'panel-body form-stack' },
      field(t('apiKeys.fullKey'), keyBox),
      el('div', { class: 'action-row' },
        button(t('common.copy'), {
          variant: 'primary',
          onClick: async () => {
            try {
              await navigator.clipboard.writeText(fullKey);
              toast(t('common.copied'), 'success');
            } catch (_) {
              toast(t('common.copyFailed'), 'error');
            }
          },
        }),
        button(t('common.close'), { onClick: onDismiss }),
      ),
    ),
  );
}

function createKeyForm(onCreated) {
  const nameInput = input({ type: 'text', maxLength: 80, autocomplete: 'off', placeholder: t('apiKeys.namePlaceholder') });
  const noteInput = textarea({ rows: 1, maxLength: 240, placeholder: t('apiKeys.notePlaceholder'), class: 'compact-textarea' });
  const submit = button(t('apiKeys.createSubmit'), { variant: 'primary' });

  submit.addEventListener('click', async () => {
    submit.disabled = true;
    submit.textContent = t('apiKeys.creating');
    try {
      const result = await api.post('/admin/gateway-keys', {
        name: nameInput.value.trim(),
        note: noteInput.value.trim(),
      });
      const data = result?.data || {};
      if (hasForbiddenField(data, CREATE_FORBIDDEN_FIELDS)) {
        toast(t('apiKeys.securityError'), 'error');
        return;
      }
      if (!data.key) {
        toast(t('apiKeys.createMissingKey'), 'error');
        return;
      }
      oneTimeSecret = data;
      nameInput.value = '';
      noteInput.value = '';
      await onCreated();
    } catch (_) {
      toast(t('apiKeys.createError'), 'error');
    } finally {
      submit.disabled = false;
      submit.textContent = t('apiKeys.createSubmit');
    }
  });

  return panel({ title: t('apiKeys.createButton'), subtitle: t('apiKeys.subtitle'), className: 'api-key-form' },
    el('div', { class: 'panel-body form-stack' },
      el('div', { class: 'form-grid' },
        field(t('apiKeys.name'), nameInput),
        field(t('apiKeys.note'), noteInput),
      ),
      el('div', { class: 'action-row' }, submit),
    ),
  );
}

function revokePanel(item, reload) {
  const prefixInput = input({ type: 'text', autocomplete: 'off', placeholder: item.key_prefix || '' });
  const confirm = button(t('apiKeys.revoke'), { variant: 'danger', disabled: true });
  const cancel = button(t('common.cancel'));
  const panelNode = panel({ title: t('apiKeys.revokeTitle'), subtitle: t('apiKeys.revokeWarning') },
    el('div', { class: 'panel-body form-stack' },
      metaGrid([
        { label: t('apiKeys.keyPrefix'), value: item.key_prefix || '-' },
        { label: t('apiKeys.name'), value: item.name || '-' },
        { label: t('apiKeys.created'), value: formatDate(item.created_at) },
      ]),
      field(t('apiKeys.revokeConfirmLabel'), prefixInput, { help: t('apiKeys.revokeConfirmHelp') }),
      el('div', { class: 'action-row' }, cancel, confirm),
    ),
  );

  prefixInput.addEventListener('input', () => {
    confirm.disabled = prefixInput.value !== item.key_prefix;
  });
  cancel.addEventListener('click', () => panelNode.remove());
  confirm.addEventListener('click', async () => {
    if (prefixInput.value !== item.key_prefix) {
      toast(t('apiKeys.revokePrefixMismatch'), 'error');
      return;
    }
    confirm.disabled = true;
    confirm.textContent = t('apiKeys.revoking');
    try {
      const result = await api.delete(`/admin/gateway-keys/${encodeURIComponent(item.id)}`);
      if (hasForbiddenField(result, REVOKE_FORBIDDEN_FIELDS)) {
        toast(t('apiKeys.securityError'), 'error');
        return;
      }
      panelNode.remove();
      await reload();
    } catch (_) {
      toast(t('apiKeys.revokeError'), 'error');
    } finally {
      confirm.disabled = false;
      confirm.textContent = t('apiKeys.revoke');
    }
  });

  return panelNode;
}

function keyCard(item, revokeSlot, reload) {
  const canRevoke = !item.revoked_at && item.key_prefix;
  const meta = [
    { label: t('apiKeys.created'), value: formatDate(item.created_at) },
    { label: t('apiKeys.lastUsed'), value: formatDate(item.last_used_at) },
  ];
  if (item.revoked_at) meta.push({ label: t('apiKeys.revokedAt'), value: formatDate(item.revoked_at) });
  if (item.note) meta.push({ label: t('apiKeys.note'), value: safeText(item.note, 80) });

  return el('article', { class: 'key-card key-compact-card' },
    el('div', { class: 'key-card-header' },
      el('div', {},
        el('p', { class: 'card-title' }, safeText(item.name || item.key_prefix || shortId(item.id), 80)),
        el('p', { class: 'card-subtitle' }, `${t('apiKeys.keyPrefix')}: ${item.key_prefix || '-'}`),
      ),
      keyStatus(item),
    ),
    metaGrid(meta),
    canRevoke ? el('div', { class: 'action-row' },
      button(t('apiKeys.revoke'), {
        size: 'sm',
        variant: 'danger',
        onClick: () => {
          revokeSlot.textContent = '';
          revokeSlot.appendChild(revokePanel(item, reload));
        },
      }),
    ) : null,
  );
}

function renderKeys(content, reload) {
  const revokeSlot = el('div');
  const visible = visibleKeys();
  const paged = pageSlice(visible, keyPage, KEY_PAGE_SIZE);
  keyPage = paged.current;
  const activeCount = keysCache.filter((item) => !item.revoked_at).length;
  const revokedCount = keysCache.length - activeCount;
  const createColumn = el('div', { class: 'api-side' },
    createKeyForm(reload),
    oneTimeSecret ? renderSecretPanel(oneTimeSecret, () => {
      oneTimeSecret = null;
      renderKeys(content, reload);
    }) : null,
    revokeSlot,
  );

  mount(content,
    pageHeader({
      kicker: t('apiKeys.kicker'),
      title: t('apiKeys.title'),
      subtitle: t('apiKeys.subtitle'),
      actions: [button(t('common.refresh'), { onClick: reload })],
    }),
    el('div', { class: 'api-layout' },
      createColumn,
      panel({},
        el('div', { class: 'keys-toolbar' },
          el('div', { class: 'action-row' },
            badge(`${activeCount} ${t('apiKeys.enabled')}`, 'success'),
            revokedCount ? badge(`${revokedCount} ${t('apiKeys.revoked')}`, 'muted') : null,
          ),
          toggle(t('apiKeys.showRevoked'), {
            checked: showRevoked,
            onchange: (event) => {
              showRevoked = event.target.checked;
              keyPage = 1;
              renderKeys(content, reload);
            },
          }),
        ),
        el('div', { class: 'keys-content' },
          visible.length ? el('div', { class: 'key-list bounded-list' }, paged.items.map((item) => keyCard(item, revokeSlot, reload))) :
            emptyState(t('apiKeys.empty')),
        ),
        paginationBar({
          page: keyPage,
          total: visible.length,
          pageSize: KEY_PAGE_SIZE,
          labels: pagerLabels(),
          onPage: (page) => {
            keyPage = page;
            renderKeys(content, reload);
          },
        }),
      ),
    ),
  );
}

export async function render() {
  const content = document.getElementById('content');

  async function reload() {
    mount(content, loadingState(t('apiKeys.loading')));
    try {
      const result = await api.get('/admin/gateway-keys');
      if (hasForbiddenField(result, LIST_FORBIDDEN_FIELDS)) {
        mount(content,
          pageHeader({ kicker: t('apiKeys.kicker'), title: t('apiKeys.title'), subtitle: t('apiKeys.subtitle') }),
          errorState(t('apiKeys.securityError')),
        );
        return;
      }
      keysCache = dataArray(result);
      keyPage = clampPage(keyPage, visibleKeys().length, KEY_PAGE_SIZE);
      renderKeys(content, reload);
    } catch (_) {
      mount(content,
        pageHeader({ kicker: t('apiKeys.kicker'), title: t('apiKeys.title'), subtitle: t('apiKeys.subtitle') }),
        errorState(t('apiKeys.error')),
      );
    }
  }

  await reload();
}

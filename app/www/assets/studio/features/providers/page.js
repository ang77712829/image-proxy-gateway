import { api } from '../../api.js';
import { t } from '../../i18n.js';
import { button } from '../../components/buttons.js';
import { badge } from '../../components/badges.js';
import { el, mount } from '../../components/dom.js';
import { field, input, select, toggle } from '../../components/forms.js';
import { pageHeader, panel, metaGrid } from '../../components/page.js';
import { emptyState, errorState, loadingState } from '../../components/states.js';
import { toast } from '../../components/toast.js';
import { formatDate, shortId } from '../../lib/format.js';

const PROVIDER_SECRET_RESPONSE_FIELDS = [
  'api_key',
  '_api_key',
  'key',
  'secret',
  '_secret',
  'token',
  'access_token',
  'password',
  'raw',
  'raw_response',
  'raw_error',
  'exception',
  'stack',
];

function hasProviderSecretField(item) {
  if (!item || typeof item !== 'object') return false;
  if (Array.isArray(item)) return item.some(hasProviderSecretField);
  return Object.keys(item).some((key) => PROVIDER_SECRET_RESPONSE_FIELDS.includes(key)) ||
    Object.values(item).some(hasProviderSecretField);
}

function dataArray(result) {
  return Array.isArray(result?.data) ? result.data : [];
}

function providerStatus(provider) {
  if (provider.enabled) return badge(t('providers.enabled'), 'success');
  return badge(t('providers.disabled'), 'muted');
}

function keyStatus(provider) {
  if (provider.api_key_configured) return badge(t('providers.configured'), 'success');
  return badge(t('providers.notConfigured'), 'warning');
}

function providerCard(provider, reload) {
  const nextEnabled = !provider.enabled;
  const toggleButton = button(nextEnabled ? t('providers.enableAction') : t('providers.disableAction'), {
    size: 'sm',
    variant: nextEnabled ? 'primary' : 'secondary',
    onClick: async () => {
      try {
        const result = await api.post(`/admin/providers/${encodeURIComponent(provider.id)}/enabled`, { enabled: nextEnabled });
        if (hasProviderSecretField(result)) {
          toast(t('providers.securityError'), 'error');
          return;
        }
        await reload();
      } catch (_) {
        toast(t('providers.updateError'), 'error');
      }
    },
  });

  return el('article', { class: 'provider-card' },
    el('div', { class: 'provider-card-header' },
      el('div', {},
        el('p', { class: 'card-title' }, provider.name || provider.id || '-'),
        el('p', { class: 'card-subtitle' }, shortId(provider.id)),
      ),
      el('div', { class: 'action-row' }, providerStatus(provider), keyStatus(provider)),
    ),
    metaGrid([
      { label: t('providers.type'), value: provider.provider_type || '-' },
      { label: t('providers.defaultModel'), value: provider.default_model || '-' },
      { label: t('providers.endpoint'), value: t('providers.endpointSummaryGap') },
      { label: t('providers.created'), value: formatDate(provider.created_at) },
      { label: t('providers.updated'), value: formatDate(provider.updated_at) },
    ]),
    el('div', { class: 'action-row' },
      toggleButton,
    ),
    el('p', { class: 'card-subtitle' }, t('providers.advancedNote')),
  );
}

function createProviderForm(reload) {
  const nameInput = input({ name: 'name', type: 'text', maxLength: 80, placeholder: t('providers.namePlaceholder') });
  const typeSelect = select([{ value: 'openai_image', label: t('providers.typeOpenAIImage') }], { name: 'provider_type' });
  const endpointInput = input({ name: 'base_url', type: 'url', placeholder: t('providers.endpointPlaceholder') });
  const modelInput = input({ name: 'default_model', type: 'text', maxLength: 120, placeholder: t('providers.defaultModelPlaceholder') });
  const secretInput = input({ name: 'api_key', type: 'password', autocomplete: 'new-password', placeholder: t('providers.secretPlaceholder') });
  const enabledToggle = toggle(t('providers.createEnabled'), { name: 'enabled', checked: true });
  const enabledInput = enabledToggle.querySelector('input');
  const submit = button(t('providers.createSubmit'), { variant: 'primary' });

  submit.addEventListener('click', async () => {
    const payload = {
      name: nameInput.value.trim(),
      provider_type: typeSelect.value,
      base_url: endpointInput.value.trim(),
      default_model: modelInput.value.trim(),
      api_key: secretInput.value.trim(),
      enabled: enabledInput.checked,
    };
    if (!payload.name || !payload.base_url || !payload.default_model) {
      toast(t('providers.createRequired'), 'error');
      return;
    }
    submit.disabled = true;
    submit.textContent = t('providers.creating');
    try {
      const result = await api.post('/admin/providers', payload);
      if (hasProviderSecretField(result)) {
        toast(t('providers.securityError'), 'error');
        return;
      }
      nameInput.value = '';
      endpointInput.value = '';
      modelInput.value = '';
      secretInput.value = '';
      enabledInput.checked = true;
      toast(t('providers.createSuccess'), 'success');
      await reload();
    } catch (_) {
      toast(t('providers.createError'), 'error');
    } finally {
      submit.disabled = false;
      submit.textContent = t('providers.createSubmit');
    }
  });

  return panel({ title: t('providers.createTitle'), subtitle: t('providers.subtitle') },
    el('div', { class: 'panel-body form-stack' },
      el('div', { class: 'form-grid' },
        field(t('providers.name'), nameInput),
        field(t('providers.type'), typeSelect),
        field(t('providers.endpoint'), endpointInput),
        field(t('providers.defaultModel'), modelInput),
        field(t('providers.secret'), secretInput),
        enabledToggle,
      ),
      el('div', { class: 'action-row' }, submit),
    ),
  );
}

function renderProviders(content, providers, reload) {
  mount(content,
    pageHeader({
      kicker: t('providers.kicker'),
      title: t('providers.title'),
      subtitle: t('providers.subtitle'),
      actions: [button(t('common.refresh'), { onClick: reload })],
    }),
    createProviderForm(reload),
    panel({ title: t('providers.title'), subtitle: t('providers.advancedNote') },
      el('div', { class: 'providers-content' },
        providers.length ? el('div', { class: 'provider-list' }, providers.map((provider) => providerCard(provider, reload))) :
          emptyState(t('providers.empty')),
      ),
    ),
  );
}

export async function render() {
  const content = document.getElementById('content');

  async function reload() {
    mount(content, loadingState(t('providers.loading')));
    try {
      const result = await api.get('/admin/providers');
      if (hasProviderSecretField(result)) {
        mount(content,
          pageHeader({ kicker: t('providers.kicker'), title: t('providers.title'), subtitle: t('providers.subtitle') }),
          errorState(t('providers.securityError')),
        );
        return;
      }
      renderProviders(content, dataArray(result), reload);
    } catch (_) {
      mount(content,
        pageHeader({ kicker: t('providers.kicker'), title: t('providers.title'), subtitle: t('providers.subtitle') }),
        errorState(t('providers.error')),
      );
    }
  }

  await reload();
}

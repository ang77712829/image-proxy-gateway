import { api } from '../../api.js';
import { t } from '../../i18n.js';
import { button, linkButton } from '../../components/buttons.js';
import { statusBadge, badge } from '../../components/badges.js';
import { el, mount } from '../../components/dom.js';
import { field, input, select, textarea } from '../../components/forms.js';
import { pageHeader, panel, metaGrid } from '../../components/page.js';
import { emptyState, errorState, loadingState } from '../../components/states.js';
import { toast } from '../../components/toast.js';
import { IMAGE_SIZE_PRESETS, isSelectableImageProvider, providerModelValue, providersFromResponse, validateCustomSize } from '../../lib/capabilities.js';
import { safeAssetHref, buildAssetDownloadName } from '../../lib/asset-url.js';
import { errorDiagnostics, safeErrorMessage } from '../../lib/safe-error.js';
import { formatDate, formatDuration, shortId, truncateText } from '../../lib/format.js';

function imageUrlFromResult(result) {
  const item = Array.isArray(result?.data) ? result.data[0] : null;
  return item?.url || '';
}

function providerOptions(providers) {
  const options = [{ value: '', label: t('generateImage.providerDefault') }];
  providers.filter(isSelectableImageProvider).forEach((provider) => {
    const model = provider.default_model ? ` · ${provider.default_model}` : '';
    options.push({
      value: providerModelValue(provider.id),
      label: `${provider.name || provider.id}${model}`,
    });
  });
  return options;
}

function customProviderByValue(providers, value) {
  if (!value || !value.startsWith('custom:')) return null;
  const id = value.slice('custom:'.length);
  return providers.find((provider) => provider.id === id) || null;
}

function recentJobCard(job) {
  return el('article', { class: `job-card ${job.status === 'failed' ? 'failed' : ''}` },
    el('div', { class: 'job-card-header' },
      el('div', {},
        el('p', { class: 'card-title' }, shortId(job.id)),
        el('p', { class: 'card-subtitle' }, truncateText(job.prompt || '-', 72)),
      ),
      statusBadge(job.status, t(`jobs.${job.status}`)),
    ),
    metaGrid([
      { label: t('jobs.provider'), value: job.provider || '-' },
      { label: t('jobs.model'), value: job.model || '-' },
      { label: t('jobs.created'), value: formatDate(job.created_at) },
    ]),
  );
}

function renderResultEmpty(target) {
  mount(target, emptyState(t('generateImage.resultEmptyTitle'), t('generateImage.resultEmptyCopy')));
}

function renderResultLoading(target) {
  mount(target, loadingState(t('generateImage.generating')));
}

function renderResultSuccess(target, result, prompt) {
  const imageUrl = safeAssetHref(imageUrlFromResult(result));
  const assetLike = {
    id: result.job_id || result.history_id || 'generated',
    prompt,
    filename: imageUrl,
    url_path: imageUrl,
    media_type: 'image',
  };

  const preview = imageUrl ?
    el('div', { class: 'preview-box' }, el('img', { class: 'result-image', src: imageUrl, alt: t('generateImage.previewAlt') })) :
    el('div', { class: 'preview-box' }, emptyState(t('generateImage.imageUnavailable')));

  mount(target,
    el('div', { class: 'result-success' },
      el('div', { class: 'job-card-header' },
        el('div', {},
          el('p', { class: 'card-title' }, t('generateImage.success')),
          el('p', { class: 'card-subtitle' }, truncateText(prompt, 120)),
        ),
        badge(t('jobs.succeeded'), 'success'),
      ),
      preview,
      imageUrl ? linkButton(t('generateImage.download'), imageUrl, {
        variant: 'primary',
        download: buildAssetDownloadName(assetLike),
      }) : null,
      metaGrid([
        { label: t('generateImage.provider'), value: result.provider },
        { label: t('generateImage.model'), value: result.model },
        { label: t('generateImage.jobId'), value: result.job_id },
        { label: t('generateImage.historyId'), value: result.history_id },
        { label: t('generateImage.duration'), value: result.duration_ms ? formatDuration(result.duration_ms) : '' },
      ]),
    ),
  );
}

function renderResultError(target, error) {
  const diagnostics = errorDiagnostics(error);
  const message = safeErrorMessage(error, error?.status === 409 ? t('generateImage.duplicate') : t('generateImage.error'));
  mount(target,
    el('div', { class: 'diagnostic-card' },
      el('p', { class: 'card-title' }, message),
      metaGrid([
        { label: t('jobs.errorCategory'), value: diagnostics.error_category },
        { label: t('jobs.gatewayStage'), value: diagnostics.gateway_stage },
        { label: t('jobs.retryable'), value: diagnostics.retryable === true ? t('jobs.retryable') : diagnostics.retryable === false ? t('jobs.notRetryable') : '' },
        { label: t('generateImage.jobId'), value: diagnostics.existing_job?.job_id },
      ]),
    ),
  );
}

async function loadProviders() {
  const result = await api.get('/admin/providers');
  return providersFromResponse(result);
}

async function loadRecentImageJobs() {
  const result = await api.get('/jobs?kind=image&limit=4&offset=0');
  return Array.isArray(result?.data) ? result.data : [];
}

function buildPage(providers, recentJobs, providerLoadFailed) {
  const providerSelect = select(providerOptions(providers), { name: 'provider' });
  const modelInput = input({ name: 'model', type: 'text', autocomplete: 'off', placeholder: t('generateImage.modelPlaceholder') });
  const sizeSelect = select(IMAGE_SIZE_PRESETS.map((item) => ({
    value: item.value,
    label: item.value === 'custom' ? t('generateImage.customSize') : item.label,
  })), { name: 'size' });
  const customSizeInput = input({
    name: 'custom_size',
    type: 'text',
    autocomplete: 'off',
    placeholder: t('generateImage.customSizePlaceholder'),
    value: '1024x1024',
  });
  const promptInput = textarea({
    name: 'prompt',
    maxLength: 32000,
    placeholder: t('generateImage.promptPlaceholder'),
  });
  const resultPanel = el('div', { class: 'result-frame' });
  const providerStatus = el('p', { class: providerLoadFailed ? 'error-text' : 'field-help' },
    providerLoadFailed ? t('generateImage.providerLoadFailed') : t('generateImage.providerHelp'),
  );
  const submit = button(t('generateImage.submit'), { variant: 'primary' });

  function syncProviderModel() {
    const provider = customProviderByValue(providers, providerSelect.value);
    if (provider) {
      modelInput.value = provider.default_model || '';
      modelInput.readOnly = true;
      modelInput.placeholder = t('generateImage.customProviderModel');
    } else {
      modelInput.readOnly = false;
      modelInput.placeholder = t('generateImage.modelPlaceholder');
    }
  }

  function syncCustomSize() {
    customSizeInput.hidden = sizeSelect.value !== 'custom';
  }

  async function submitGeneration() {
    const prompt = promptInput.value.trim();
    if (!prompt) {
      toast(t('generateImage.promptRequired'), 'error');
      promptInput.focus();
      return;
    }

    let size = sizeSelect.value || '1024x1024';
    if (size === 'custom') {
      const validation = validateCustomSize(customSizeInput.value);
      if (!validation.ok) {
        toast(t(validation.messageKey), 'error');
        customSizeInput.focus();
        return;
      }
      size = validation.value;
    }

    const payload = {
      prompt,
      response_format: 'url',
      size: size,
    };
    if (providerSelect.value) {
      payload.model = providerSelect.value;
    } else if (modelInput.value.trim()) {
      payload.model = modelInput.value.trim();
    }

    submit.disabled = true;
    submit.textContent = t('generateImage.generating');
    renderResultLoading(resultPanel);
    try {
      const result = await api.post('/images/generations', payload);
      renderResultSuccess(resultPanel, result, prompt);
    } catch (error) {
      renderResultError(resultPanel, error);
    } finally {
      submit.disabled = false;
      submit.textContent = t('generateImage.submit');
    }
  }

  providerSelect.addEventListener('change', syncProviderModel);
  sizeSelect.addEventListener('change', syncCustomSize);
  submit.addEventListener('click', submitGeneration);
  syncProviderModel();
  syncCustomSize();
  renderResultEmpty(resultPanel);

  return [
    pageHeader({
      kicker: t('generateImage.kicker'),
      title: t('generateImage.title'),
      subtitle: t('generateImage.subtitle'),
    }),
    el('div', { class: 'generate-grid' },
      panel({ title: t('generateImage.title') },
        el('div', { class: 'panel-body form-stack' },
          field(t('generateImage.prompt'), promptInput, { className: 'span-2' }),
          el('div', { class: 'form-grid' },
            field(t('generateImage.provider'), providerSelect, { help: providerStatus.textContent }),
            field(t('generateImage.model'), modelInput),
            field(t('generateImage.size'), sizeSelect),
            field(t('generateImage.customSize'), customSizeInput),
          ),
          providerStatus,
          el('div', { class: 'action-row' }, submit),
        ),
      ),
      panel({ title: t('generateImage.preview') },
        el('div', { class: 'panel-body' }, resultPanel),
      ),
    ),
    panel({ title: t('generateImage.recentImages') },
      el('div', { class: 'panel-body' },
        recentJobs.length ? el('div', { class: 'recent-strip' }, recentJobs.map(recentJobCard)) :
          emptyState(t('generateImage.noRecentJobs')),
      ),
    ),
  ];
}

export async function render() {
  const content = document.getElementById('content');
  mount(content, loadingState(t('common.loading')));

  let providers = [];
  let providerLoadFailed = false;
  try {
    providers = await loadProviders();
  } catch (_) {
    providerLoadFailed = true;
  }

  try {
    const recentJobs = await loadRecentImageJobs();
    mount(content, buildPage(providers, recentJobs, providerLoadFailed));
  } catch (_) {
    mount(content,
      pageHeader({ kicker: t('generateImage.kicker'), title: t('generateImage.title'), subtitle: t('generateImage.subtitle') }),
      errorState(t('generateImage.error')),
    );
  }
}

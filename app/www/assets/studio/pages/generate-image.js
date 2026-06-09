import { api } from '../api.js';
import { t } from '../i18n.js';

const DEFAULT_PROVIDER_VALUE = '';
const CUSTOM_PROVIDER_TYPE = 'openai_image';
const IMAGE_SIZES = ['1024x1024', '1024x1536', '1536x1024'];

// 安全校验：只允许同源图片 URL
function isSafeImageUrl(url) {
  try {
    const parsed = new URL(url, window.location.origin);
    // 只允许同源
    if (parsed.origin !== window.location.origin) return false;
    // 只允许 /generated/ 或 /uploads/ 路径
    return parsed.pathname.startsWith('/generated/') || parsed.pathname.startsWith('/uploads/');
  } catch (_) {
    return false;
  }
}

function createField(labelText, control) {
  const label = document.createElement('label');
  label.className = 'field-label form-field';
  label.textContent = labelText;
  label.appendChild(control);
  return label;
}

function createSizeSelect() {
  const select = document.createElement('select');
  select.className = 'form-control';
  select.name = 'size';
  IMAGE_SIZES.forEach(size => {
    const option = document.createElement('option');
    option.value = size;
    option.textContent = size;
    select.appendChild(option);
  });
  select.value = '1024x1024';
  return select;
}

function createProviderSelect() {
  const select = document.createElement('select');
  select.className = 'form-control';
  select.name = 'provider';

  const option = document.createElement('option');
  option.value = DEFAULT_PROVIDER_VALUE;
  option.textContent = t('generateImage.providerDefault');
  select.appendChild(option);

  return select;
}

function providerArrayFromResponse(result) {
  if (Array.isArray(result?.data)) return result.data;
  if (Array.isArray(result)) return result;
  return [];
}

function isEnabledImageProvider(item) {
  return Boolean(
    item &&
    typeof item === 'object' &&
    item.enabled === true &&
    item.provider_type === CUSTOM_PROVIDER_TYPE &&
    item.id
  );
}

function providerOptionText(item) {
  const name = item.name || item.id;
  if (item.default_model) {
    return `${name} (${t('generateImage.model')}: ${item.default_model})`;
  }
  return name;
}

async function loadProviderOptions(select, status) {
  try {
    const result = await api.get('/admin/providers');
    providerArrayFromResponse(result)
      .filter(isEnabledImageProvider)
      .forEach(item => {
        const option = document.createElement('option');
        option.value = `custom:${item.id}`;
        option.textContent = providerOptionText(item);
        select.appendChild(option);
      });
  } catch (_) {
    status.textContent = t('generateImage.providerLoadFailed');
    status.className = 'text-muted';
  }
}

function isDuplicateError(err) {
  return err?.status === 409 || String(err?.message || '').includes('duplicate_in_flight_job');
}

export async function render() {
  const content = document.getElementById('content');
  content.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'page-header';
  const heading = document.createElement('h1');
  heading.className = 'page-heading';
  heading.textContent = t('generateImage.title');
  header.appendChild(heading);
  content.appendChild(header);

  const card = document.createElement('div');
  card.className = 'card section-card';

  const promptLabel = document.createElement('label');
  promptLabel.className = 'field-label form-field';
  promptLabel.textContent = t('generateImage.prompt');

  const promptInput = document.createElement('textarea');
  promptInput.rows = 4;
  promptInput.placeholder = t('generateImage.promptPlaceholder');
  promptInput.className = 'form-control';
  promptLabel.appendChild(promptInput);
  card.appendChild(promptLabel);

  const providerSelect = createProviderSelect();
  const providerStatus = document.createElement('p');
  providerStatus.className = 'text-muted';
  card.appendChild(createField(t('generateImage.provider'), providerSelect));
  card.appendChild(providerStatus);

  const sizeSelect = createSizeSelect();
  card.appendChild(createField(t('generateImage.size'), sizeSelect));

  const actions = document.createElement('div');
  actions.className = 'form-actions';
  const submitBtn = document.createElement('button');
  submitBtn.className = 'btn btn-primary';
  submitBtn.textContent = t('generateImage.submit');
  actions.appendChild(submitBtn);
  card.appendChild(actions);

  const statusDiv = document.createElement('div');
  statusDiv.className = 'result-panel';
  card.appendChild(statusDiv);

  content.appendChild(card);

  await loadProviderOptions(providerSelect, providerStatus);

  submitBtn.addEventListener('click', async () => {
    const prompt = promptInput.value.trim();

    // 空 prompt 验证
    if (!prompt) {
      statusDiv.textContent = '';
      const errorText = document.createElement('p');
      errorText.textContent = t('generateImage.promptRequired');
      errorText.className = 'error-text';
      statusDiv.appendChild(errorText);
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = t('generateImage.generating');
    statusDiv.textContent = '';

    try {
      const payload = {
        prompt,
        response_format: 'url',
        size: sizeSelect.value || '1024x1024',
      };

      if (providerSelect.value && providerSelect.value.startsWith('custom:')) {
        payload.model = providerSelect.value;
      }

      const result = await api.post('/images/generations', payload);

      const successText = document.createElement('p');
      successText.textContent = t('generateImage.success');
      successText.className = 'text-success';
      statusDiv.appendChild(successText);

      // 显示图片预览（安全校验）
      const imageUrl = result?.data?.[0]?.url;
      if (imageUrl && isSafeImageUrl(imageUrl)) {
        const img = document.createElement('img');
        img.src = imageUrl;
        img.alt = t('generateImage.previewAlt');
        img.className = 'result-image';
        statusDiv.appendChild(img);
      } else {
        const fallback = document.createElement('p');
        fallback.textContent = t('generateImage.imageUnavailable');
        fallback.className = 'preview-fallback';
        statusDiv.appendChild(fallback);
      }

      // 显示元信息
      if (result.duration_ms || result.provider || result.model) {
        const meta = document.createElement('p');
        meta.className = 'result-meta';
        const parts = [];
        if (result.provider) parts.push(`${t('generateImage.provider')}: ${result.provider}`);
        if (result.model) parts.push(`${t('generateImage.model')}: ${result.model}`);
        if (result.duration_ms) parts.push(`${t('generateImage.duration')}: ${result.duration_ms}ms`);
        meta.textContent = parts.join(' | ');
        statusDiv.appendChild(meta);
      }
    } catch (err) {
      // 只显示通用错误，不暴露后端细节
      const errorText = document.createElement('p');
      errorText.textContent = isDuplicateError(err) ? t('generateImage.duplicate') : t('generateImage.error');
      errorText.className = 'error-text';
      statusDiv.appendChild(errorText);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = t('generateImage.submit');
    }
  });
}

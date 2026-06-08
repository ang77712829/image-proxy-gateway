import { api } from '../api.js';
import { t } from '../i18n.js';

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

export async function render() {
  const content = document.getElementById('content');
  content.innerHTML = '';

  const card = document.createElement('div');
  card.className = 'card';

  const h2 = document.createElement('h2');
  h2.textContent = t('generateImage.title');
  card.appendChild(h2);

  const promptLabel = document.createElement('label');
  promptLabel.className = 'field-label';
  promptLabel.textContent = t('generateImage.prompt');

  const promptInput = document.createElement('textarea');
  promptInput.rows = 4;
  promptInput.placeholder = t('generateImage.promptPlaceholder');
  promptInput.style.width = '100%';
  promptInput.style.marginTop = '8px';
  promptLabel.appendChild(promptInput);
  card.appendChild(promptLabel);

  const submitBtn = document.createElement('button');
  submitBtn.className = 'btn btn-primary';
  submitBtn.textContent = t('generateImage.submit');
  submitBtn.style.marginTop = '12px';
  card.appendChild(submitBtn);

  const statusDiv = document.createElement('div');
  statusDiv.style.marginTop = '16px';
  card.appendChild(statusDiv);

  content.appendChild(card);

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
      const result = await api.post('/images/generations', {
        prompt,
        response_format: 'url',
      });

      const successText = document.createElement('p');
      successText.textContent = t('generateImage.success');
      successText.style.color = '#27ae60';
      statusDiv.appendChild(successText);

      // 显示图片预览（安全校验）
      const imageUrl = result?.data?.[0]?.url;
      if (imageUrl && isSafeImageUrl(imageUrl)) {
        const img = document.createElement('img');
        img.src = imageUrl;
        img.alt = t('generateImage.previewAlt');
        img.style.maxWidth = '100%';
        img.style.marginTop = '12px';
        img.style.borderRadius = '8px';
        statusDiv.appendChild(img);
      } else {
        const fallback = document.createElement('p');
        fallback.textContent = t('generateImage.imageUnavailable');
        fallback.style.color = '#666';
        fallback.style.fontStyle = 'italic';
        statusDiv.appendChild(fallback);
      }

      // 显示元信息
      if (result.duration_ms || result.provider || result.model) {
        const meta = document.createElement('p');
        meta.style.fontSize = '12px';
        meta.style.color = '#888';
        meta.style.marginTop = '8px';
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
      errorText.textContent = t('generateImage.error');
      errorText.className = 'error-text';
      statusDiv.appendChild(errorText);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = t('generateImage.submit');
    }
  });
}

import { t } from '../../i18n.js';
import {
  imageSizeOptions,
  validateCustomSize,
} from '../../lib/capabilities.js';
import { replaceOptions } from './catalog-state.js';

export function syncSizeFields(sizeSelect, customSizeInput) {
  customSizeInput.hidden = sizeSelect.value !== 'custom';
}

export function syncSizeOptions({
  sizeSelect,
  customSizeInput,
  sizeCapabilityWarning,
  catalogProviderId,
  customProvider,
  model,
}) {
  const options = imageSizeOptions(model);
  replaceOptions(sizeSelect, options);
  const presets = Array.isArray(model?.size_presets) ? model.size_presets : [];
  sizeSelect.value = presets[0] || 'custom';
  if (catalogProviderId) {
    sizeCapabilityWarning.textContent = t('generateImage.sizeCapabilityCatalogUnknown');
    sizeCapabilityWarning.hidden = presets.length > 0;
  } else if (customProvider) {
    sizeCapabilityWarning.textContent = t('generateImage.sizeCapabilityCustomUnknown');
    sizeCapabilityWarning.hidden = false;
  } else {
    sizeCapabilityWarning.textContent = t('generateImage.sizeCapabilityDefaultHint');
    sizeCapabilityWarning.hidden = false;
  }
  syncSizeFields(sizeSelect, customSizeInput);
}

export function selectedSize(sizeSelect, customSizeInput) {
  let size = sizeSelect.value || 'custom';
  if (size !== 'custom') {
    return { ok: true, value: size };
  }

  const validation = validateCustomSize(customSizeInput.value);
  if (!validation.ok) {
    return validation;
  }
  size = validation.value;
  return { ok: true, value: size };
}

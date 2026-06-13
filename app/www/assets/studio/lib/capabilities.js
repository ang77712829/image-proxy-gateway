export const IMAGE_SIZE_PRESETS = [
  { value: '1024x1024', label: '1024 x 1024' },
  { value: '1024x1536', label: '1024 x 1536' },
  { value: '1536x1024', label: '1536 x 1024' },
  { value: 'custom', label: 'Custom' },
];

export const IMAGE_CAPABILITY_SEED = {
  default: {
    supportsCustomSize: true,
    presets: IMAGE_SIZE_PRESETS.map((item) => item.value).filter((value) => value !== 'custom'),
  },
};

export function validateCustomSize(value) {
  const match = String(value || '').trim().match(/^([1-9]\d{1,3})x([1-9]\d{1,3})$/i);
  if (!match) {
    return { ok: false, messageKey: 'generateImage.sizeInvalidFormat' };
  }
  const width = Number(match[1]);
  const height = Number(match[2]);
  if (width < 256 || height < 256 || width > 4096 || height > 4096) {
    return { ok: false, messageKey: 'generateImage.sizeInvalidRange' };
  }
  return { ok: true, value: `${width}x${height}` };
}

export function providersFromResponse(result) {
  if (Array.isArray(result?.data)) return result.data;
  if (Array.isArray(result)) return result;
  return [];
}

export function isSelectableImageProvider(item) {
  return Boolean(
    item &&
    typeof item === 'object' &&
    item.enabled === true &&
    item.provider_type === 'openai_image' &&
    item.id
  );
}

export function providerModelValue(providerId) {
  return `custom:${providerId}`;
}

export function providersFromCatalog(result) {
  return Array.isArray(result?.providers) ? result.providers : [];
}

export function modelsFromCatalog(result) {
  return Array.isArray(result?.models) ? result.models : [];
}

export function selectableVideoModels(result) {
  return modelsFromCatalog(result).filter((item) => (
    item &&
    typeof item === 'object' &&
    item.media_type === 'video' &&
    item.selectable === true &&
    item.id
  ));
}

export function videoProvidersForModels(result, models) {
  const providerIds = new Set(models.map((item) => item.provider_id).filter(Boolean));
  return providersFromCatalog(result).filter((item) => providerIds.has(item.id));
}

export function parseSizePreset(value) {
  const match = String(value || '').trim().match(/^([1-9]\d{1,3})x([1-9]\d{1,3})$/i);
  if (!match) return null;
  return { width: Number(match[1]), height: Number(match[2]) };
}

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

export function selectableImageModels(result) {
  return modelsFromCatalog(result).filter((item) => (
    item &&
    typeof item === 'object' &&
    item.media_type === 'image' &&
    item.selectable === true &&
    item.status === 'release' &&
    item.id
  ));
}

export function videoProvidersForModels(result, models) {
  const providerIds = new Set(models.map((item) => item.provider_id).filter(Boolean));
  return providersFromCatalog(result).filter((item) => providerIds.has(item.id));
}

export function imageProvidersForModels(result, models) {
  const providerIds = new Set(models.map((item) => item.provider_id).filter(Boolean));
  return providersFromCatalog(result).filter((item) => providerIds.has(item.id));
}

export function imageSizeOptions(model) {
  const presets = Array.isArray(model?.size_presets) ? model.size_presets : [];
  return [
    ...presets.map((preset) => ({ value: preset, label: preset })),
    { value: 'custom', label: 'Custom' },
  ];
}

export function parseSizePreset(value) {
  const match = String(value || '').trim().match(/^([1-9]\d{1,3})x([1-9]\d{1,3})$/i);
  if (!match) return null;
  return { width: Number(match[1]), height: Number(match[2]) };
}

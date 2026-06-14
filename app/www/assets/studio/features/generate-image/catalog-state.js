import { api } from '../../api.js';
import { t } from '../../i18n.js';
import { el } from '../../components/dom.js';
import {
  imageProvidersForModels,
  isSelectableImageProvider,
  providerModelValue,
  providersFromResponse,
  selectableImageModels,
} from '../../lib/capabilities.js';

export function option(label, value, disabled = false) {
  return { label, value, disabled };
}

export function providerLabel(provider) {
  return provider?.display_name || provider?.name || provider?.id || '-';
}

export function modelProvider(providers, model) {
  return providers.find((provider) => provider.id === model?.provider_id) || null;
}

export function modelLabel(providers, model) {
  const provider = modelProvider(providers, model);
  const prefix = provider ? `${providerLabel(provider)} / ` : '';
  return `${prefix}${model.display_name || model.id}`;
}

export function routeModelValue(model) {
  const aliases = Array.isArray(model?.aliases) ? model.aliases.filter(Boolean) : [];
  return aliases[0] || model?.id || '';
}

export function catalogProviderValue(providerId) {
  return `catalog:${providerId}`;
}

export function catalogProviderIdFromValue(value) {
  return value && value.startsWith('catalog:') ? value.slice('catalog:'.length) : '';
}

export function customProviderByValue(providers, value) {
  if (!value || !value.startsWith('custom:')) return null;
  const id = value.slice('custom:'.length);
  return providers.find((provider) => provider.id === id) || null;
}

export function modelsForProvider(models, providerId) {
  return models.filter((model) => !providerId || model.provider_id === providerId);
}

export function modelById(models, id) {
  return models.find((model) => model.id === id) || null;
}

export function replaceOptions(node, items) {
  node.textContent = '';
  items.forEach((item) => {
    node.appendChild(el('option', { value: item.value, disabled: item.disabled }, item.label));
  });
}

export function providerOptions(catalogProviders, customProviders) {
  const options = [option(t('generateImage.providerDefault'), '')];
  catalogProviders.forEach((provider) => {
    options.push(option(providerLabel(provider), catalogProviderValue(provider.id)));
  });
  customProviders.forEach((provider) => {
    const model = provider.default_model ? ` - ${provider.default_model}` : '';
    options.push(option(`${provider.name || provider.id}${model}`, providerModelValue(provider.id)));
  });
  return options;
}

export function buildCatalogState(catalog, customProviders) {
  const catalogModels = selectableImageModels(catalog);
  const catalogProviders = imageProvidersForModels(catalog, catalogModels);
  return { catalogModels, catalogProviders, customProviders };
}

export async function loadCatalog() {
  return api.get('/admin/catalog');
}

export async function loadProviders() {
  const result = await api.get('/admin/providers');
  return providersFromResponse(result).filter(isSelectableImageProvider);
}

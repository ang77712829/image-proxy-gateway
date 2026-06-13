"""Safe API projection for the static provider catalog."""
from __future__ import annotations

from typing import Any

from .schema import ModelCatalogEntry, ProviderCatalog, ProviderCatalogEntry


def catalog_api_response(catalog: ProviderCatalog) -> dict[str, Any]:
    """Return the catalog fields that are safe and useful for admin UI clients."""

    return {
        "object": "provider_catalog",
        "providers": [_provider_entry(item, catalog) for item in catalog.providers],
        "models": [_model_entry(item) for item in catalog.models],
    }


def _provider_entry(provider: ProviderCatalogEntry, catalog: ProviderCatalog) -> dict[str, Any]:
    provider_models = [model for model in catalog.models if model.provider == provider.id]
    default_orders = [
        model.default_chain_order
        for model in provider_models
        if model.default_chain_order is not None
    ]
    media_types = list(provider.media_types)
    return {
        "id": provider.id,
        "display_name": provider.display_name,
        "media_type": media_types[0] if len(media_types) == 1 else "multi",
        "media_types": media_types,
        "status": provider.status,
        "enabled_default": provider.enabled_default,
        "config_enabled_key": provider.config_enabled_key,
        "requires_key": provider.requires_key,
        "adapter_id": provider.adapter_id,
        "ui_group": provider.ui_group,
        "selectable": any(model.selectable for model in provider_models),
        "default_chain_order": min(default_orders) if default_orders else None,
        "tags": [],
    }


def _model_entry(model: ModelCatalogEntry) -> dict[str, Any]:
    return {
        "id": model.id,
        "provider_id": model.provider,
        "provider_model": model.provider_model,
        "media_type": model.media_type,
        "display_name": model.display_name,
        "aliases": list(model.aliases),
        "status": model.status,
        "selectable": model.selectable,
        "default_chain_order": model.default_chain_order,
        "capabilities": dict(model.capabilities),
        "params": dict(model.params),
        "size_presets": list(model.size_presets),
        "ref_inputs": dict(model.ref_inputs),
        "extra_allowlist": list(model.extra_allowlist),
        "tags": list(model.tags),
    }

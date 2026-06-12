"""Static provider catalog schema.

The catalog is data only: it describes built-in providers and models, but it
does not import adapter code or change runtime routing by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


VALID_PROVIDER_STATUSES = {"release", "experimental", "reserved"}
VALID_MODEL_STATUSES = {"release", "experimental", "reserved"}
VALID_MEDIA_TYPES = {"image", "video"}
VALID_CAPABILITIES = {
    "text_to_image",
    "image_to_image",
    "text_to_video",
    "image_to_video",
}


@dataclass(frozen=True)
class ProviderCatalogEntry:
    id: str
    display_name: str
    media_types: tuple[str, ...]
    status: str
    enabled_default: bool
    config_enabled_key: str | None
    requires_key: bool
    credential_keys: tuple[str, ...]
    adapter_id: str
    ui_group: str
    notes: str


@dataclass(frozen=True)
class ModelCatalogEntry:
    id: str
    provider: str
    provider_model: str
    media_type: str
    display_name: str
    aliases: tuple[str, ...]
    status: str
    selectable: bool
    default_chain_order: int | None
    capabilities: dict[str, bool]
    params: dict[str, Any]
    size_presets: tuple[str, ...]
    ref_inputs: dict[str, Any]
    extra_allowlist: tuple[str, ...]
    tags: tuple[str, ...]


@dataclass(frozen=True)
class ProviderCatalog:
    providers: tuple[ProviderCatalogEntry, ...]
    models: tuple[ModelCatalogEntry, ...]

    @property
    def providers_by_id(self) -> dict[str, ProviderCatalogEntry]:
        return {item.id: item for item in self.providers}

    @property
    def models_by_id(self) -> dict[str, ModelCatalogEntry]:
        return {item.id: item for item in self.models}

    def default_image_chain(self) -> list[ModelCatalogEntry]:
        return sorted(
            (
                model
                for model in self.models
                if model.media_type == "image" and model.default_chain_order is not None
            ),
            key=lambda item: item.default_chain_order or 0,
        )

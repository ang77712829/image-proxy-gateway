"""Load and validate the local static provider catalog."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .schema import (
    ProviderCatalog,
    ProviderCatalogEntry,
    ModelCatalogEntry,
    VALID_CAPABILITIES,
    VALID_MEDIA_TYPES,
    VALID_MODEL_STATUSES,
    VALID_PROVIDER_STATUSES,
)


CATALOG_DIR = Path(__file__).resolve().parent
PROVIDERS_FILE = "providers.yaml"
MODELS_FILE = "models.yaml"

PROVIDERS_TOP_KEYS = {"providers"}
MODELS_TOP_KEYS = {"models"}
PROVIDER_KEYS = {
    "id",
    "display_name",
    "media_types",
    "status",
    "enabled_default",
    "config_enabled_key",
    "requires_key",
    "credential_keys",
    "adapter_id",
    "ui_group",
    "notes",
}
MODEL_KEYS = {
    "id",
    "provider",
    "provider_model",
    "media_type",
    "display_name",
    "aliases",
    "status",
    "selectable",
    "default_chain_order",
    "capabilities",
    "params",
    "size_presets",
    "ref_inputs",
    "extra_allowlist",
    "tags",
}
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SAFE_ADAPTER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")


class CatalogValidationError(ValueError):
    """Raised when the static provider catalog is invalid."""


def load_provider_catalog(catalog_dir: Path | None = None) -> ProviderCatalog:
    base_dir = catalog_dir or CATALOG_DIR
    providers_raw = _load_yaml_mapping(base_dir / PROVIDERS_FILE, allowed_top_keys=PROVIDERS_TOP_KEYS)
    models_raw = _load_yaml_mapping(base_dir / MODELS_FILE, allowed_top_keys=MODELS_TOP_KEYS)
    providers = _parse_providers(providers_raw.get("providers"))
    models = _parse_models(models_raw.get("models"), providers)
    return ProviderCatalog(providers=tuple(providers), models=tuple(models))


def _load_yaml_mapping(path: Path, *, allowed_top_keys: set[str]) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise CatalogValidationError(f"{path.name} must contain a mapping")
    _reject_unknown_keys(path.name, data, allowed_top_keys)
    return data


def _parse_providers(raw_items: Any) -> list[ProviderCatalogEntry]:
    if not isinstance(raw_items, list):
        raise CatalogValidationError("providers must be a list")

    seen: set[str] = set()
    providers: list[ProviderCatalogEntry] = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise CatalogValidationError(f"provider[{index}] must be a mapping")
        _reject_unknown_keys(f"provider[{index}]", raw, PROVIDER_KEYS)
        _require_keys(f"provider[{index}]", raw, PROVIDER_KEYS)

        provider_id = _require_safe_id(f"provider[{index}].id", raw["id"])
        if provider_id in seen:
            raise CatalogValidationError(f"duplicate provider id: {provider_id}")
        seen.add(provider_id)

        media_types = _string_tuple(f"provider[{index}].media_types", raw["media_types"])
        if not media_types:
            raise CatalogValidationError(f"provider {provider_id} must declare at least one media type")
        invalid_media = set(media_types) - VALID_MEDIA_TYPES
        if invalid_media:
            raise CatalogValidationError(f"provider {provider_id} has invalid media type: {sorted(invalid_media)[0]}")

        status = _require_status(f"provider[{index}].status", raw["status"], VALID_PROVIDER_STATUSES)
        enabled_default = _require_bool(f"provider[{index}].enabled_default", raw["enabled_default"])
        if status == "reserved" and enabled_default:
            raise CatalogValidationError(f"reserved provider {provider_id} cannot be enabled by default")

        adapter_id = _require_string(f"provider[{index}].adapter_id", raw["adapter_id"])
        if not SAFE_ADAPTER_ID_RE.match(adapter_id):
            raise CatalogValidationError(f"provider {provider_id} adapter_id must be a safe registry id")

        providers.append(
            ProviderCatalogEntry(
                id=provider_id,
                display_name=_require_string(f"provider[{index}].display_name", raw["display_name"]),
                media_types=media_types,
                status=status,
                enabled_default=enabled_default,
                config_enabled_key=_optional_string(f"provider[{index}].config_enabled_key", raw["config_enabled_key"]),
                requires_key=_require_bool(f"provider[{index}].requires_key", raw["requires_key"]),
                credential_keys=_string_tuple(f"provider[{index}].credential_keys", raw["credential_keys"]),
                adapter_id=adapter_id,
                ui_group=_require_string(f"provider[{index}].ui_group", raw["ui_group"]),
                notes=_require_string(f"provider[{index}].notes", raw["notes"]),
            )
        )
    return providers


def _parse_models(raw_items: Any, providers: list[ProviderCatalogEntry]) -> list[ModelCatalogEntry]:
    if not isinstance(raw_items, list):
        raise CatalogValidationError("models must be a list")

    providers_by_id = {provider.id: provider for provider in providers}
    seen: set[str] = set()
    models: list[ModelCatalogEntry] = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise CatalogValidationError(f"model[{index}] must be a mapping")
        _reject_unknown_keys(f"model[{index}]", raw, MODEL_KEYS)
        _require_keys(f"model[{index}]", raw, MODEL_KEYS)

        model_id = _require_safe_id(f"model[{index}].id", raw["id"])
        if model_id in seen:
            raise CatalogValidationError(f"duplicate model id: {model_id}")
        seen.add(model_id)

        provider_id = _require_safe_id(f"model[{index}].provider", raw["provider"])
        provider = providers_by_id.get(provider_id)
        if provider is None:
            raise CatalogValidationError(f"model {model_id} references unknown provider: {provider_id}")

        media_type = _require_status(f"model[{index}].media_type", raw["media_type"], VALID_MEDIA_TYPES)
        if media_type not in provider.media_types:
            raise CatalogValidationError(f"model {model_id} media_type is not supported by provider {provider_id}")

        status = _require_status(f"model[{index}].status", raw["status"], VALID_MODEL_STATUSES)
        selectable = _require_bool(f"model[{index}].selectable", raw["selectable"])
        default_chain_order = _optional_int(f"model[{index}].default_chain_order", raw["default_chain_order"])
        if default_chain_order is not None and (status != "release" or provider.status != "release"):
            raise CatalogValidationError(f"model {model_id} cannot enter default chain unless provider and model are release")
        if status == "reserved" and selectable:
            raise CatalogValidationError(f"reserved model {model_id} cannot be selectable")

        capabilities = _capabilities(f"model[{index}].capabilities", raw["capabilities"])
        models.append(
            ModelCatalogEntry(
                id=model_id,
                provider=provider_id,
                provider_model=_require_string(f"model[{index}].provider_model", raw["provider_model"]),
                media_type=media_type,
                display_name=_require_string(f"model[{index}].display_name", raw["display_name"]),
                aliases=_string_tuple(f"model[{index}].aliases", raw["aliases"]),
                status=status,
                selectable=selectable,
                default_chain_order=default_chain_order,
                capabilities=capabilities,
                params=_dict(f"model[{index}].params", raw["params"]),
                size_presets=_string_tuple(f"model[{index}].size_presets", raw["size_presets"]),
                ref_inputs=_dict(f"model[{index}].ref_inputs", raw["ref_inputs"]),
                extra_allowlist=_string_tuple(f"model[{index}].extra_allowlist", raw["extra_allowlist"]),
                tags=_string_tuple(f"model[{index}].tags", raw["tags"]),
            )
        )
    return models


def _reject_unknown_keys(label: str, value: dict[str, Any], allowed_keys: set[str]) -> None:
    unknown = set(value) - allowed_keys
    if unknown:
        raise CatalogValidationError(f"{label} has unknown key: {sorted(unknown)[0]}")


def _require_keys(label: str, value: dict[str, Any], required_keys: set[str]) -> None:
    missing = required_keys - set(value)
    if missing:
        raise CatalogValidationError(f"{label} is missing key: {sorted(missing)[0]}")


def _require_safe_id(label: str, value: Any) -> str:
    text = _require_string(label, value)
    if not SAFE_ID_RE.match(text):
        raise CatalogValidationError(f"{label} must be a safe id")
    return text


def _require_status(label: str, value: Any, allowed: set[str]) -> str:
    text = _require_string(label, value)
    if text not in allowed:
        raise CatalogValidationError(f"{label} has invalid value: {text}")
    return text


def _require_string(label: str, value: Any) -> str:
    if not isinstance(value, str):
        raise CatalogValidationError(f"{label} must be a string")
    text = value.strip()
    if not text:
        raise CatalogValidationError(f"{label} must not be empty")
    return text


def _optional_string(label: str, value: Any) -> str | None:
    if value is None:
        return None
    return _require_string(label, value)


def _require_bool(label: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise CatalogValidationError(f"{label} must be a boolean")
    return value


def _optional_int(label: str, value: Any) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise CatalogValidationError(f"{label} must be an integer or null")
    return value


def _string_tuple(label: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise CatalogValidationError(f"{label} must be a list")
    items: list[str] = []
    for index, item in enumerate(value):
        items.append(_require_string(f"{label}[{index}]", item))
    return tuple(items)


def _dict(label: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CatalogValidationError(f"{label} must be a mapping")
    return dict(value)


def _capabilities(label: str, value: Any) -> dict[str, bool]:
    data = _dict(label, value)
    unknown = set(data) - VALID_CAPABILITIES
    if unknown:
        raise CatalogValidationError(f"{label} has unknown capability: {sorted(unknown)[0]}")
    for key, item in data.items():
        if not isinstance(item, bool):
            raise CatalogValidationError(f"{label}.{key} must be a boolean")
    return dict(data)

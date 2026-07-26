from typing import TYPE_CHECKING

from .mulerun import MuleRunProvider
from .apimart import ApimartProvider
from .atlascloud import AtlasCloudProvider
from .agnes import AgnesProvider
from .volcengine import VolcengineProvider

if TYPE_CHECKING:
    from .base import BaseProvider

_PROVIDERS = {
    "mulerun": MuleRunProvider,
    "apimart": ApimartProvider,
    "atlascloud": AtlasCloudProvider,
    "agnes": AgnesProvider,
    "volcengine": VolcengineProvider,
}


def get_provider(name: str, api_key: str) -> "BaseProvider":
    """Return an instantiated provider by name."""
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider: {name}")
    return cls(api_key)


def get_provider_class(name: str) -> type["BaseProvider"]:
    """Return the provider class (for accessing class-level attributes like env_var)."""
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider: {name}")
    return cls


def list_providers() -> list[str]:
    """Return all registered provider names."""
    return list(_PROVIDERS.keys())

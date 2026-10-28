"""Provider registry and runtime selection."""

import importlib
import pkgutil

from backend.app.core.config import Settings, get_settings
from backend.app.core.schemas import ModelInfo
from backend.app.providers import __path__ as provider_path
from backend.app.providers.base import BaseLLMProvider, ProviderRegistration


class ProviderRegistry:
    """Create providers and track the active provider."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.active_provider_id = settings.active_provider
        self._registrations = self._discover_registrations()

    @staticmethod
    def _discover_registrations() -> dict[str, ProviderRegistration]:
        """Load provider modules that export `get_provider_registration`."""
        package_name = "backend.app.providers"
        registrations: dict[str, ProviderRegistration] = {}
        for module_info in pkgutil.iter_modules(provider_path, f"{package_name}."):
            if module_info.name.endswith((".base", ".registry")):
                continue
            module = importlib.import_module(module_info.name)
            factory = getattr(module, "get_provider_registration", None)
            if factory is None:
                continue
            registration = factory()
            if registration.provider_id in registrations:
                raise ValueError(f"Duplicate provider id: {registration.provider_id}")
            registrations[registration.provider_id] = registration
        return registrations

    def definitions(self) -> dict[str, tuple[ProviderRegistration, str, bool, str | None]]:
        """Return provider metadata resolved from the current settings."""
        definitions = {}
        for provider_id, registration in self._registrations.items():
            available, detail = registration.get_availability(self.settings)
            definitions[provider_id] = (
                registration,
                registration.get_model(self.settings),
                available,
                detail,
            )
        return definitions

    def create(self, provider_id: str | None = None) -> BaseLLMProvider:
        """Instantiate the selected provider."""
        selected = provider_id or self.active_provider_id
        definition = self.definitions().get(selected)
        if definition is None:
            raise ValueError(f"Unknown provider: {selected}")
        registration, _, available, detail = definition
        if not available:
            raise ValueError(detail or f"{registration.display_name} is not configured.")
        return registration.create(self.settings)

    def models(self) -> list[ModelInfo]:
        """Return model choices for the UI."""
        return [
            ModelInfo(
                id=provider_id,
                name=registration.display_name,
                model=model,
                available=available,
                active=provider_id == self.active_provider_id,
                detail=detail,
            )
            for provider_id, (registration, model, available, detail) in self.definitions().items()
        ]


registry = ProviderRegistry(get_settings())

"""Provider failures independent of HTTP frameworks and individual models."""


class ProviderError(Exception):
    """An upstream provider could not fulfill the request."""


class ProviderUnavailableError(ProviderError):
    """The provider cannot currently be reached or is unavailable."""


class ProviderTimeoutError(ProviderError):
    """The provider exceeded its request timeout."""


class InvalidProviderResponseError(ProviderError):
    """The provider returned an invalid or empty response."""


class InvalidProviderError(ProviderError):
    """The caller selected an unknown provider."""


class ProviderAuthorizationError(ProviderError):
    """Upstream rejected the server's provider credentials."""


class ProviderConfigurationError(ProviderError):
    """The selected provider is not correctly configured."""

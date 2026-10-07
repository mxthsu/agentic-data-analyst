class ModelProviderError(RuntimeError):
    """Erro controlado de integração com o provedor de modelo."""


class ModelRateLimitError(ModelProviderError):
    """Cota ou limite de requisições atingido."""


class ModelTimeoutError(ModelProviderError):
    """O provedor não respondeu dentro do tempo limite."""


class ModelAuthenticationError(ModelProviderError):
    """A credencial do provedor é inválida ou não autorizada."""


class ModelUnavailableError(ModelProviderError):
    """O provedor ou modelo está temporariamente indisponível."""

import os

from .azure_provider import AzureOpenAIProvider
from .claude_provider import ClaudeProvider

_PROVIDERS = {
    "claude": ClaudeProvider,
    "azure": AzureOpenAIProvider,
}


def _provider():
    provider_adi = os.getenv("LLM_PROVIDER", "azure").lower()
    try:
        provider_sinifi = _PROVIDERS[provider_adi]
    except KeyError:
        raise ValueError(
            f"Bilinmeyen LLM_PROVIDER: '{provider_adi}'. Geçerli seçenekler: {list(_PROVIDERS)}"
        )
    return provider_sinifi()


def get_llm():
    return _provider().get_llm()


def get_fast_llm():
    return _provider().get_fast_llm()

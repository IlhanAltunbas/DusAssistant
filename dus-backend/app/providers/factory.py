import os

from .azure_provider import AzureOpenAIProvider
from .claude_provider import ClaudeProvider

_PROVIDERS = {
    "claude": ClaudeProvider,
    "azure": AzureOpenAIProvider,
}


def get_llm():
    provider_adi = os.getenv("LLM_PROVIDER", "azure").lower()
    try:
        provider_sinifi = _PROVIDERS[provider_adi]
    except KeyError:
        raise ValueError(
            f"Bilinmeyen LLM_PROVIDER: '{provider_adi}'. Geçerli seçenekler: {list(_PROVIDERS)}"
        )
    return provider_sinifi().get_llm()

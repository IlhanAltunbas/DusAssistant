import os

from langchain_anthropic import ChatAnthropic

from .base import LLMProvider


class ClaudeProvider(LLMProvider):
    def get_llm(self):
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            temperature=0,
            # Azure tarafıyla aynı politika: geçici hatalarda SDK içinde 2 tekrar (toplam 3 deneme).
            max_retries=2,
        )

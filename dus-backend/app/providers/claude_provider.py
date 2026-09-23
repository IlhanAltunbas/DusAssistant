import os

from langchain_anthropic import ChatAnthropic

from .base import LLMProvider


class ClaudeProvider(LLMProvider):
    def get_llm(self):
        return ChatAnthropic(
            model_name=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            temperature=0,
        )

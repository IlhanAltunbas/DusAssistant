from abc import ABC, abstractmethod
from langchain_core.language_models.chat_models import BaseChatModel


class LLMProvider(ABC):
    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """RAG zincirine takılabilecek, LangChain uyumlu bir chat modeli döner."""
        raise NotImplementedError

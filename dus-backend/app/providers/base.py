from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel


class LLMProvider(ABC):
    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """RAG zincirine takılabilecek, LangChain uyumlu bir chat modeli döner."""
        raise NotImplementedError

    def get_fast_llm(self) -> BaseChatModel:
        """Soru yeniden yazma gibi kısa, düşünme gerektirmeyen işler için model.
        Varsayılan olarak normal modeldir; provider'lar daha hızlı bir ayar sunabilir."""
        return self.get_llm()

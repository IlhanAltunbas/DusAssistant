import os

from langchain_openai import AzureChatOpenAI

from .base import LLMProvider


class AzureOpenAIProvider(LLMProvider):
    def get_llm(self):
        # gpt-5 ailesi reasoning modeli: varsayılan ayarda cevap süresinin yarısı gizli düşünmeye gidiyor.
        return self._olustur(os.getenv("AZURE_OPENAI_REASONING_EFFORT", "low"))

    def get_fast_llm(self):
        # Soru yeniden yazma düşünme gerektirmiyor; minimal ile reasoning token'ı 0'a iniyor.
        return self._olustur("minimal")

    def _olustur(self, reasoning_effort: str):
        return AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            temperature=1,
            # Geçici hatalarda SDK'nın kendi tekrar denemesi (toplam 3 deneme); tek retry katmanı bu.
            max_retries=2,
            model_kwargs={"reasoning_effort": reasoning_effort},
        )

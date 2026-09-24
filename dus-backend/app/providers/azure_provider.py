import os

from langchain_openai import AzureChatOpenAI

from .base import LLMProvider


class AzureOpenAIProvider(LLMProvider):
    def get_llm(self):
        return AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            temperature=1,
            # gpt-5 ailesi reasoning modeli: varsayılan ayarda cevap süresinin yarısı gizli düşünmeye gidiyor.
            model_kwargs={"reasoning_effort": os.getenv("AZURE_OPENAI_REASONING_EFFORT", "low")},
        )

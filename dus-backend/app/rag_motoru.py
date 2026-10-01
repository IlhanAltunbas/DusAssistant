import logging
import time
from dataclasses import dataclass

import anthropic
import openai
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate

from .dil import soru_dili
from .providers.factory import get_fast_llm, get_llm
from .retrievers.factory import get_retriever

# Tekrar deneme tek katmanda, SDK'ların içinde yapılır: openai, anthropic ve Azure AI Search istemcileri
# geçici hatalarda (429, 408, 5xx, bağlantı) sadece başarısız çağrıyı tekrar dener ve Retry-After'a uyar.
# Üstüne ikinci bir retry katmanı eklemek denemeleri katlıyordu (1 soru -> 12 LLM isteği).
# Bu liste SDK denemeleri tükendikten sonra kullanıcıya hangi mesajın gösterileceğine karar verir.
GECICI_HATALAR = (
    anthropic.RateLimitError,
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
)


load_dotenv()

logger = logging.getLogger("uvicorn.error")

llm = get_llm()
hizli_llm = get_fast_llm()

# ---------------------------------------------------------------------------
# Cevap dili (tespit: dil.py)
# ---------------------------------------------------------------------------
_DILLER = {
    "tr": ("Turkish", "Bu kaynakların içinde bu soruya dair bir bilgi yok."),
    "en": ("English", "There is no information about this question in these sources."),
}


# ---------------------------------------------------------------------------
# Promptlar
# ---------------------------------------------------------------------------
system_template = """You are an expert periodontology assistant for DUS, the Turkish dental specialty exam.
Answer using ONLY the source texts (Context) below; never add facts that are not in them.
If the sources contain information relevant to the question, answer with it, even if it only partially covers the question.
Only if the sources contain nothing relevant to the question, reply with just this sentence: "{bilgi_yok}"

Source texts (Context):
{context}

Write your answer in {cevap_dili}. The source texts may be in another language; translate as needed."""

prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(system_template),
    ("placeholder", "{chat_history}"),
    # Dil talimatı sorunun hemen arkasında da tekrarlanır; uzun context araya girince sistem
    # mesajındaki kural zayıflıyordu. Geçmişe bu not değil, sadece soru kaydedilir.
    HumanMessagePromptTemplate.from_template("{question}\n\n(Answer in {cevap_dili}.)"),
])
cevap_zinciri = prompt | llm | StrOutputParser()

# Arama sadece son soruyu görür. "Bunlardan hangisi en güçlüsü?" gibi bir takip sorusunda konu
# (periodontitis) sorguda geçmediği için doğru parça geriye düşüyordu. Geçmiş varsa soru önce
# geçmişe bakmadan anlaşılır hale getirilir; cevabı üreten LLM ise orijinal soruyu ve geçmişi görür.
yeniden_yazma_promptu = ChatPromptTemplate.from_messages([
    ("system", (
        "Rewrite the user's latest question as a standalone question that can be understood "
        "without the chat history, replacing words like 'these' or 'it' with what they refer to. "
        "Keep the language of the question. Do NOT answer it. If it is already standalone, "
        "return it unchanged. Return only the question."
    )),
    ("placeholder", "{chat_history}"),
    ("human", "{question}"),
])
sorgu_yeniden_yazici = yeniden_yazma_promptu | hizli_llm | StrOutputParser()

retriever = get_retriever()


def dokumanlari_birlestir(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def gecmisi_cevir(gecmis: list | None) -> list:
    mesajlar = []
    for msg in gecmis or []:
        if msg.startswith("User:"):
            mesajlar.append(HumanMessage(content=msg.replace("User: ", "", 1)))
        elif msg.startswith("Assistant:"):
            mesajlar.append(AIMessage(content=msg.replace("Assistant: ", "", 1)))
    return mesajlar


def arama_sorgusu(soru: str, gecmis_mesajlari: list) -> str:
    # İlk soruda geçmiş yok; ek LLM çağrısına gerek yok. Eval de bu fonksiyonu kullanır,
    # böylece ölçülen arama production'dakiyle aynıdır.
    if not gecmis_mesajlari:
        return soru
    return sorgu_yeniden_yazici.invoke({"question": soru, "chat_history": gecmis_mesajlari})


@dataclass
class Cevap:
    metin: str
    # Cevabın dayandığı parçalar; eval'deki hakem cevabın bunlara sadık olup olmadığını kontrol eder.
    dokumanlar: list
    sorgu: str
    dil: str


def cevap_uret(soru: str, gecmis: list | None = None) -> Cevap:
    gecmis_mesajlari = gecmisi_cevir(gecmis)
    dil = soru_dili(soru)
    cevap_dili, bilgi_yok = _DILLER[dil]

    t0 = time.perf_counter()
    arama = arama_sorgusu(soru, gecmis_mesajlari)
    t1 = time.perf_counter()
    dokumanlar = retriever.invoke(arama)
    t2 = time.perf_counter()
    cevap = cevap_zinciri.invoke({
        "question": soru,
        "chat_history": gecmis_mesajlari,
        "context": dokumanlari_birlestir(dokumanlar),
        "cevap_dili": cevap_dili,
        "bilgi_yok": bilgi_yok,
    })
    t3 = time.perf_counter()

    # Soru metni loglanmaz (kullanıcı verisi); yavaşlığın hangi adımda olduğunu görmek için süreler.
    logger.info(
        "/ask dil=%s takip=%s | yeniden yazma %.1f sn, arama %.1f sn, cevap %.1f sn, toplam %.1f sn",
        dil, bool(gecmis_mesajlari), t1 - t0, t2 - t1, t3 - t2, t3 - t0,
    )
    return Cevap(metin=cevap, dokumanlar=dokumanlar, sorgu=arama, dil=dil)


def asistana_sor(soru: str, gecmis: list | None = None) -> str:
    return cevap_uret(soru, gecmis).metin


if __name__ == "__main__":
    # Test Senaryosu
    test_gecmis = ["User: Merhaba!", "Assistant: Merhaba, ben bir Periodontoloji uzmanıyım."]
    test_sorusu = "Ben sana az önce ne dedim?" 
    
    print(f"Soru: {test_sorusu}")
    yanit = asistana_sor(test_sorusu, test_gecmis)
    print("Asistanın Cevabı:", yanit)

    
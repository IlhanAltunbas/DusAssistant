"""Agent modu: model kitaplarda ne zaman, hangi sorguyla ve kaç kez arayacağına kendisi karar verir.

Zincirde (rag_motoru.py) akış sabittir: soruyu yeniden yaz, bir kez ara, cevapla. Eval'de en zayıf yer
çapraz dil soruları çıktı: Türkçe soru Türkçe parçaları getiriyor, cevap İngilizce kitaptaysa bulunamıyor.
Agent ilk aramada bulamazsa diğer dilde tekrar arayabilir. Bedeli daha fazla LLM çağrısı, daha uzun
süre ve her çalıştırmada farklı bir yol; hangisinin kullanılacağına eval karar verir (asistan.py).

    START → model ──(araç istemedi)─────────────→ END
              └──(araç istedi)→ ara ──(tur < sınır)→ model
                                    └─(tur = sınır)→ son_cevap → END

Sınırlar kodda: ilk turda arama zorunlu, en fazla AGENT_MAX_STEPS arama turu ve turda 2 arama, sonra araçsız
son cevap. Agent boş cevap üretirse zincire düşülür.
"""
import logging
import os
import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, ConfigDict, Field

from .dil import soru_dili
from .rag_motoru import _DILLER, Cevap, gecmisi_cevir, llm, retriever
from .rag_motoru import cevap_uret as zincir_cevap_uret

logger = logging.getLogger("uvicorn.error")

# Her tur bir LLM çağrısı (birkaç saniye). 3 tur: bir arama, bulamazsa diğer dilde bir arama, bir düzeltme hakkı.
ADIM_SINIRI = int(os.getenv("AGENT_MAX_STEPS", "3"))
# Bir turda en fazla kaç arama: her dil için bir tane.
TUR_BASINA_ARAMA = 2

SISTEM = """You are an expert periodontology assistant for DUS, the Turkish dental specialty exam.
You can read four periodontology textbooks only through the kitaplarda_ara tool: two in Turkish, two in English.
Answer using ONLY the passages the tool returned; never add facts that are not in them.
Every statement in your answer must be written in the passages. Do not add details the passages do not state, even \
if you know them to be true: no direction of an effect, numbers, item-by-item mappings, causes or explanations that \
are not there. Translating and summarising the passages is fine.
If the passages contain information relevant to the question, answer with it, even if it only partially covers the \
question. Information about a different substance, drug, procedure or condition than the one asked about is not \
relevant.
Only if the passages contain nothing relevant after searching in both languages, reply with just this sentence: "{bilgi_yok}"

Write your answer in {cevap_dili}, in your own words. The passages may be in another language: translate them, \
and do not quote them in their original language."""

ARAC_ACIKLAMASI = (
    "Searches the periodontology textbooks and returns the 5 most relevant passages with their book and page. "
    "A search mostly returns passages in the language of the query. If the results do not answer the question, "
    "search again in the other language. To search both languages at once, call the tool twice in the same turn."
)


class AramaArgumanlari(BaseModel):
    # extra="forbid": model fazladan ya da yanlış adlı argüman gönderirse ToolNode aracı çalıştırmaz,
    # hatayı modele geri verir; model bir sonraki turda düzeltebilir.
    model_config = ConfigDict(extra="forbid")
    sorgu: str = Field(description=(
        "A standalone natural-language question or sentence in Turkish or English, the way the textbook would "
        "phrase the topic, understandable without the chat history. Not a keyword list; do not name the language."
    ))


def arama_araci(retriever):
    # content_and_artifact: model metni görür; Document'lar mesajın artifact alanında kalır ve cevabın
    # dayandığı parçalar olarak eval'deki hakeme gider (zincirdeki Cevap.dokumanlar ile aynı rol).
    @tool("kitaplarda_ara", description=ARAC_ACIKLAMASI, args_schema=AramaArgumanlari,
          response_format="content_and_artifact")
    def kitaplarda_ara(sorgu: str):
        dokumanlar = retriever.invoke(sorgu)
        metin = "\n\n".join(
            f"[{d.metadata.get('source', '?')}, p.{d.metadata.get('page', -1) + 1}]\n{d.page_content}"
            for d in dokumanlar
        )
        return metin, dokumanlar

    return kitaplarda_ara


class Durum(MessagesState):
    # messages: düğümlerin döndürdüğü mesajlar listeye eklenir. adim: modelin araçlı tur sayısı.
    adim: int


def _son_model_mesaji(mesajlar: list) -> AIMessage:
    return next(m for m in reversed(mesajlar) if isinstance(m, AIMessage))


def ajan_olustur(model, retriever, adim_siniri: int = ADIM_SINIRI, tur_basina_arama: int = TUR_BASINA_ARAMA):
    arac = arama_araci(retriever)
    # İlk turda arama kodla zorunlu: model kitaplara bakmadan kendi bilgisinden cevap veremez. "any" hem
    # OpenAI'de ("required"e çevrilir) hem Claude'da geçerli; "required" Claude'da araç adı sanılıyor.
    ilk_tur = model.bind_tools([arac], tool_choice="any")
    sonraki_turlar = model.bind_tools([arac])

    def karar(durum: Durum) -> dict:
        secilen = ilk_tur if durum["adim"] == 0 else sonraki_turlar
        yanit = secilen.invoke(durum["messages"])
        if len(yanit.tool_calls) > tur_basina_arama:
            # Tur sınırı tur sayar; bir turda istenen arama sayısı da sınırlanmazsa tek turda onlarca paralel
            # arama (her biri embedding + Azure Search çağrısı) istenebilir. Fazlası mesajdan çıkarılır;
            # API'ye geri gönderilen geçmiş tool_calls alanından üretildiği için iz kalmaz.
            logger.warning("Agent bir turda %d arama istedi, %d ile sınırlandı", len(yanit.tool_calls), tur_basina_arama)
            yanit = yanit.model_copy(update={"tool_calls": yanit.tool_calls[:tur_basina_arama]})
        # Argümanları JSON olarak çözülemeyen çağrılar invalid_tool_calls'a düşer ve ToolNode onları görmez.
        # API her araç çağrısının bir cevabı olmasını istediği için hata mesajı burada eklenir; model düzeltebilir.
        hatalar = [
            ToolMessage(
                f"Error: the arguments could not be parsed ({c.get('error') or 'invalid JSON'}). "
                "Call kitaplarda_ara again with a valid JSON object containing 'sorgu'.",
                tool_call_id=c["id"], status="error",
            )
            for c in yanit.invalid_tool_calls
        ]
        return {"messages": [yanit, *hatalar], "adim": durum["adim"] + 1}

    def son_cevap(durum: Durum) -> dict:
        # Tur sınırı doldu: bulunan pasajlar düz metin olarak verilir ve araçsız cevap istenir. Araç geçmişi
        # gönderilmez: Claude araç blokları içeren bir istekte araç tanımı da ister; düz metin her sağlayıcıda
        # çalışır ve daha kısadır.
        mesajlar = durum["messages"]
        soru_sirasi = max(i for i, m in enumerate(mesajlar) if isinstance(m, HumanMessage))
        pasajlar = "\n\n".join(
            m.text for m in mesajlar[soru_sirasi + 1:] if isinstance(m, ToolMessage) and m.status != "error"
        )
        istem = [
            *mesajlar[:soru_sirasi],
            HumanMessage(f"Passages found by your searches:\n\n{pasajlar or '(none)'}\n\n{mesajlar[soru_sirasi].text}"),
        ]
        return {"messages": [model.invoke(istem)]}

    def karardan_sonra(durum: Durum) -> str:
        son = _son_model_mesaji(durum["messages"])
        if son.tool_calls:
            return "ara"
        # Sadece bozuk çağrı vardı: hata mesajları eklendi, tur sınırına göre modele ya da son cevaba.
        return aramadan_sonra(durum) if son.invalid_tool_calls else END

    def aramadan_sonra(durum: Durum) -> str:
        return "son_cevap" if durum["adim"] >= adim_siniri else "model"

    graf = StateGraph(Durum)
    graf.add_node("model", karar)
    graf.add_node("ara", ToolNode([arac]))
    graf.add_node("son_cevap", son_cevap)
    graf.add_edge(START, "model")
    graf.add_conditional_edges("model", karardan_sonra, ["ara", "model", "son_cevap", END])
    graf.add_conditional_edges("ara", aramadan_sonra, ["model", "son_cevap"])
    graf.add_edge("son_cevap", END)
    # recursion_limit LangGraph'ın emniyet kemeri: graf bir hata yüzünden döngüden çıkamazsa hata fırlatır.
    # Normal en uzun yol: sınır x (model + ara) + son_cevap.
    return graf.compile().with_config(recursion_limit=2 * adim_siniri + 4)


ajan = ajan_olustur(llm, retriever)


def cevap_uret(soru: str, gecmis: list | None = None, graf=None) -> Cevap:
    graf = graf or ajan
    gecmis_mesajlari = gecmisi_cevir(gecmis)
    dil = soru_dili(soru)
    cevap_dili, bilgi_yok = _DILLER[dil]
    mesajlar = [
        SystemMessage(SISTEM.format(cevap_dili=cevap_dili, bilgi_yok=bilgi_yok)),
        *gecmis_mesajlari,
        # Zincirdeki gibi dil talimatı sorunun arkasında da tekrarlanır.
        HumanMessage(f"{soru}\n\n(Answer in {cevap_dili}.)"),
    ]

    t0 = time.perf_counter()
    sonuc = graf.invoke({"messages": mesajlar, "adim": 0})
    sure = time.perf_counter() - t0

    yeni = sonuc["messages"][len(mesajlar):]
    sorgular = [c["args"].get("sorgu", "") for m in yeni if isinstance(m, AIMessage) for c in m.tool_calls]
    dokumanlar, gorulen = [], set()
    for m in yeni:
        if isinstance(m, ToolMessage):
            for d in m.artifact or []:  # hata mesajlarında artifact yok
                anahtar = (d.metadata.get("source"), d.metadata.get("page"), d.page_content)
                if anahtar not in gorulen:
                    gorulen.add(anahtar)
                    dokumanlar.append(d)
    metin = str(yeni[-1].text).strip()

    # Soru metni loglanmaz (kullanıcı verisi).
    logger.info(
        "/ask agent dil=%s takip=%s | %d tur, %d arama, %.1f sn",
        dil, bool(gecmis_mesajlari), sonuc["adim"], len(sorgular), sure,
    )
    if not metin:
        # Kullanıcıya boş cevap gösterilmez ve sohbet geçmişine boş mesaj yazılmaz: sabit zincire düşülür.
        logger.warning("Agent boş cevap üretti, zincire düşülüyor")
        return zincir_cevap_uret(soru, gecmis)
    return Cevap(metin=metin, dokumanlar=dokumanlar, sorgu=" | ".join(sorgular), dil=dil, arama_sayisi=len(sorgular))

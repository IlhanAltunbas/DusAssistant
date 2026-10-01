"""Framework kullanmadan tool calling: agent döngüsünün kendisi.

LangGraph'a geçmeden önce, bir agent'ın aslında ne yaptığını görmek için. Döngü:
  1. Modele soru + araç tanımları gönderilir.
  2. Model ya cevap verir ya da "şu aracı şu argümanlarla çağır" der (tool_calls).
  3. Aracı biz çalıştırırız (model hiçbir şeyi kendisi çalıştırmaz), sonucu konuşmaya ekleriz.
  4. 2. adıma dönülür. Döngüyü sınırlayan şey bizim kodumuz: en fazla ADIM_SINIRI tur.

dus-backend klasöründen:
    python -m deneyler.elle_arac_cagirma "Köprü destek dişleri kök yüzey alanına göre nasıl seçilir?"
"""
import json
import os
import sys

from dotenv import load_dotenv
from openai import AzureOpenAI

from app.dil import soru_dili
from app.retrievers.factory import get_retriever

load_dotenv()

ADIM_SINIRI = 4

istemci = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
)
DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]
retriever = get_retriever()

# Modelin gördüğü tek şey bu tanım: adı, ne işe yaradığı ve argümanlarının JSON şeması.
# Açıklama, modelin aracı ne zaman ve nasıl kullanacağını belirler; kodun kendisini model hiç görmez.
ARACLAR = [{
    "type": "function",
    "function": {
        "name": "kitaplarda_ara",
        "description": (
            "Searches the periodontology textbooks and returns the 5 most relevant passages with their "
            "book and page. Two books are in Turkish and two in English, and a search mostly returns "
            "passages in the language of the query. If the results do not answer the question, search "
            "again in the other language."
        ),
        "parameters": {
            "type": "object",
            "properties": {"sorgu": {"type": "string", "description": (
                "A natural-language question or sentence in Turkish or English, the way the textbook would "
                "phrase the topic. Not a keyword list; do not name the language in the query."
            )}},
            "required": ["sorgu"],
            "additionalProperties": False,
        },
    },
}]

SISTEM = (
    "You are a periodontology assistant for the Turkish dental specialty exam (DUS). Answer only from "
    "passages returned by the kitaplarda_ara tool and cite book and page. If the passages do not contain "
    "the answer after searching in both languages, say that the sources do not contain it. "
    "Write your final answer in {dil}, even when the passages are in another language."
)
# "Sorunun dilinde cevap ver" demek yetmiyor: Türkçe kaynak okuyan model İngilizce soruya Türkçe
# cevap verdi. Uygulamadaki (v7) çözümün aynısı: dil kodla tespit edilip açıkça yazılır.
DIL_ADI = {"tr": "Turkish", "en": "English"}


def kitaplarda_ara(sorgu: str) -> str:
    dokumanlar = retriever.invoke(sorgu)
    return json.dumps([
        {"kitap": d.metadata["source"], "sayfa": d.metadata["page"] + 1, "metin": d.page_content}
        for d in dokumanlar
    ], ensure_ascii=False)


def calistir(soru: str) -> str:
    sistem = SISTEM.format(dil=DIL_ADI[soru_dili(soru)])
    mesajlar = [{"role": "system", "content": sistem}, {"role": "user", "content": soru}]

    for adim in range(1, ADIM_SINIRI + 1):
        yanit = istemci.chat.completions.create(
            model=DEPLOYMENT, messages=mesajlar, tools=ARACLAR, reasoning_effort="low",
        )
        mesaj = yanit.choices[0].message

        if not mesaj.tool_calls:
            print(f"\n[adım {adim}] model cevap verdi")
            return mesaj.content

        # Modelin araç isteği de konuşmanın parçası: geri gönderilmezse model kendi isteğini hatırlamaz.
        mesajlar.append(mesaj.model_dump(exclude_none=True))
        for cagri in mesaj.tool_calls:
            argumanlar = json.loads(cagri.function.arguments)
            print(f"\n[adım {adim}] model istiyor: {cagri.function.name}({argumanlar})")
            sonuc = kitaplarda_ara(**argumanlar)
            bulunanlar = [f"{p['kitap'][:28]} s.{p['sayfa']}" for p in json.loads(sonuc)]
            print(f"          biz çalıştırdık, dönen: {bulunanlar}")
            # tool_call_id: model birden fazla araç istediyse hangi sonucun hangisine ait olduğunu bilsin.
            mesajlar.append({"role": "tool", "tool_call_id": cagri.id, "content": sonuc})

    # Bütçe bitti: araç vermeden son bir kez sor, model elindekilerle cevap versin.
    print(f"\n[sınır] {ADIM_SINIRI} adım doldu, araçsız son cevap isteniyor")
    yanit = istemci.chat.completions.create(model=DEPLOYMENT, messages=mesajlar, reasoning_effort="low")
    return yanit.choices[0].message.content


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    soru = " ".join(sys.argv[1:]) or "Köprü destek dişleri kök yüzey alanına göre nasıl seçilir?"
    print(f"SORU: {soru}")
    print(f"\nCEVAP:\n{calistir(soru)}")

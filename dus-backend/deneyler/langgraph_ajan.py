"""elle_arac_cagirma.py'deki agent döngüsünün LangGraph ile aynısı.

Araç, sistem mesajı, adım sınırı ve dil kuralı oradan alınıyor; değişen tek şey döngüyü kimin yürüttüğü.
Elle yazılan for döngüsünün yerini bir graf alıyor:

    START → model ──(araç istemedi)───────────────→ END
              │
              └──(araç istedi)→ araclar ──(adım < sınır)→ model
                                        └─(adım = sınır)→ son_cevap → END

dus-backend klasöründen:
    python -m deneyler.langgraph_ajan "Köprü destek dişleri kök yüzey alanına göre nasıl seçilir?"
"""
import json
import sys

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, ConfigDict, Field

from app.dil import soru_dili
from app.providers.factory import get_llm
from deneyler.elle_arac_cagirma import ADIM_SINIRI, ARACLAR, DIL_ADI, SISTEM, kitaplarda_ara

_TANIM = ARACLAR[0]["function"]


# Elle yazdığımız JSON şemasını burada pydantic üretiyor. Kontrol edildi: modele giden şema, elle yazılanla
# "additionalProperties": false dışında aynı; LangChain o alanı (strict modu açılmadıkça) göndermiyor.
# Elle yazılan versiyondan farklı olarak ToolNode argümanları bu modele göre doğruluyor: model "sorgu" yerine
# "soru" gönderirse araç çalışmıyor, hata mesajı modele geri dönüyor ve model düzeltebiliyor.
class AramaArgumanlari(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sorgu: str = Field(description=_TANIM["parameters"]["properties"]["sorgu"]["description"])


@tool("kitaplarda_ara", description=_TANIM["description"], args_schema=AramaArgumanlari)
def kitaplarda_ara_araci(sorgu: str) -> str:
    return kitaplarda_ara(sorgu)


llm = get_llm()  # uygulamanın kendi modeli (Azure OpenAI, reasoning_effort ve retry ayarlarıyla)
llm_araclarla = llm.bind_tools([kitaplarda_ara_araci])


class Durum(MessagesState):
    # "messages" MessagesState'ten gelir: düğümlerin döndürdüğü mesajlar listeye eklenir, üzerine yazılmaz.
    # Elle yazılan versiyondaki mesajlar.append(...) satırlarının yerini bu alır.
    adim: int


def model(durum: Durum) -> dict:
    return {"messages": [llm_araclarla.invoke(durum["messages"])], "adim": durum["adim"] + 1}


def son_cevap(durum: Durum) -> dict:
    # Bütçe bitti: araç bağlanmamış model, elindeki pasajlarla cevap verir.
    return {"messages": [llm.invoke(durum["messages"])]}


def model_sonrasi(durum: Durum) -> str:
    return "araclar" if durum["messages"][-1].tool_calls else END


def araclar_sonrasi(durum: Durum) -> str:
    return "son_cevap" if durum["adim"] >= ADIM_SINIRI else "model"


graf = StateGraph(Durum)
graf.add_node("model", model)
# ToolNode: modelin istediği araçları çalıştırır, sonucu tool_call_id ile eşleştirip ToolMessage olarak ekler.
graf.add_node("araclar", ToolNode([kitaplarda_ara_araci]))
graf.add_node("son_cevap", son_cevap)
graf.add_edge(START, "model")
graf.add_conditional_edges("model", model_sonrasi, ["araclar", END])
graf.add_conditional_edges("araclar", araclar_sonrasi, ["model", "son_cevap"])
graf.add_edge("son_cevap", END)
ajan = graf.compile()

# Bizim sınırımız zarif bitiş sağlar (son_cevap). recursion_limit ise LangGraph'ın emniyet kemeri: graf bir
# hata yüzünden döngüden çıkamazsa bu kadar düğüm adımından sonra hata fırlatır. En uzun yol: 4 x (model +
# araclar) + son_cevap = 9 adım.
AYAR = {"recursion_limit": 2 * ADIM_SINIRI + 2}


def calistir(soru: str) -> str:
    baslangic = {
        "messages": [SystemMessage(SISTEM.format(dil=DIL_ADI[soru_dili(soru)])), HumanMessage(soru)],
        "adim": 0,
    }
    son_mesaj = None
    # stream_mode="updates": her düğüm bittiğinde o düğümün durumda değiştirdiği kısım gelir.
    for parca in ajan.stream(baslangic, AYAR, stream_mode="updates"):
        for dugum, guncelleme in parca.items():
            for mesaj in guncelleme["messages"]:
                if dugum == "model" and mesaj.tool_calls:
                    for cagri in mesaj.tool_calls:
                        print(f"\n[{dugum}, adım {guncelleme['adim']}] model istiyor: {cagri['name']}({cagri['args']})")
                elif dugum == "araclar":
                    bulunanlar = [f"{p['kitap'][:28]} s.{p['sayfa']}" for p in json.loads(mesaj.content)]
                    print(f"[{dugum}] ToolNode çalıştırdı, dönen: {bulunanlar}")
                else:
                    print(f"\n[{dugum}] cevap verdi")
                son_mesaj = mesaj
    return son_mesaj.content


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    soru = " ".join(sys.argv[1:]) or "Köprü destek dişleri kök yüzey alanına göre nasıl seçilir?"
    print(f"SORU: {soru}")
    print(f"\nCEVAP:\n{calistir(soru)}")

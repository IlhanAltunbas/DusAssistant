"""Agent'ın kodla uygulanan kuralları. Model ve arama sahte: ağa çıkılmaz, para harcanmaz, sonuç her
seferinde aynıdır. Gerçek modelin cevap kalitesi burada değil, eval'de ölçülür."""
import importlib

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app import ajan, asistan


class SahteArama:
    def __init__(self):
        self.sorgular = []

    def invoke(self, sorgu):
        self.sorgular.append(sorgu)
        return [Document(page_content=f"{sorgu} hakkında metin", metadata={"source": "kitap.pdf", "page": 9})]


def mesaj_sirasi_gecerli(mesajlar):
    """API kuralı: modelin her araç çağrısına (bozuk JSON'lu olanlar dahil), sonraki model ya da kullanıcı
    mesajından önce aynı id'li bir ToolMessage gelmeli. Gerçek API kuralı bozan isteği 400 ile reddeder."""
    bekleyen = set()
    for m in mesajlar:
        if isinstance(m, ToolMessage):
            assert m.tool_call_id in bekleyen, f"cevaplanacak çağrı yok: {m.tool_call_id}"
            bekleyen.discard(m.tool_call_id)
            continue
        assert not bekleyen, f"cevapsız araç çağrısı: {bekleyen}"
        if isinstance(m, AIMessage):
            bekleyen = {c["id"] for c in [*m.tool_calls, *m.invalid_tool_calls]}
    assert not bekleyen, f"cevapsız araç çağrısı: {bekleyen}"


class SahteModel:
    """Yazılan cevapları sırayla döndürür. Her çağrının araç ayarını ve gördüğü mesajları kaydeder,
    mesaj sırasının API kuralına uyduğunu her çağrıda kontrol eder."""

    def __init__(self, cevaplar, son_cevap="elimdekilerle cevap"):
        self.cevaplar = list(cevaplar)
        self.son_cevap = son_cevap
        self.cagrilar = []  # (araç ayarı, mesajlar)

    def bind_tools(self, araclar, tool_choice=None):
        model = self

        class Bagli:
            def invoke(self, mesajlar):
                mesaj_sirasi_gecerli(mesajlar)
                model.cagrilar.append((tool_choice or "auto", list(mesajlar)))
                return model.cevaplar.pop(0)

        return Bagli()

    def invoke(self, mesajlar):
        mesaj_sirasi_gecerli(mesajlar)
        self.cagrilar.append(("araçsız", list(mesajlar)))
        return AIMessage(self.son_cevap)


def arama_iste(*sorgular, argumanlar=None):
    tum_argumanlar = [argumanlar] if argumanlar else [{"sorgu": s} for s in sorgular]
    return AIMessage("", tool_calls=[
        {"name": "kitaplarda_ara", "args": a, "id": f"c{i}"} for i, a in enumerate(tum_argumanlar)
    ])


def bozuk_json_ile_arama():
    # Model argümanları geçersiz JSON olarak yazınca langchain çağrıyı invalid_tool_calls'a koyar.
    return AIMessage("", invalid_tool_calls=[
        {"name": "kitaplarda_ara", "args": '{"sorgu": "Ante', "id": "bozuk", "error": "JSON çözülemedi"}
    ])


def calistir(model_cevaplari, soru="Ante kanunu nedir?", gecmis=None, sinir=3):
    model, arama = SahteModel(model_cevaplari), SahteArama()
    cevap = ajan.cevap_uret(soru, gecmis, graf=ajan.ajan_olustur(model, arama, adim_siniri=sinir))
    return cevap, model, arama


def test_arar_ve_bulunanlarla_cevap_verir():
    cevap, model, arama = calistir([arama_iste("Ante kanunu nedir?"), AIMessage("Destek dişlerinin kök yüzeyi...")])

    assert cevap.metin == "Destek dişlerinin kök yüzeyi..."
    assert arama.sorgular == ["Ante kanunu nedir?"]
    assert cevap.arama_sayisi == 1
    # Bulunan parçalar hakem için Cevap'ta; model metni kitap ve 1'den başlayan sayfayla görür.
    assert [d.metadata["page"] for d in cevap.dokumanlar] == [9]
    arac_sonucu = model.cagrilar[1][1][-1]
    assert isinstance(arac_sonucu, ToolMessage) and "[kitap.pdf, p.10]" in arac_sonucu.content


def test_ilk_turda_arama_zorunlu_sonra_serbest():
    _, model, _ = calistir([arama_iste("Ante"), AIMessage("cevap")])
    assert [ayar for ayar, _ in model.cagrilar] == ["any", "auto"]


def test_tur_siniri_dolunca_aracsiz_son_cevap():
    # Model hep arama istiyor; kod 3 turdan sonra durdurup araç vermeden cevap istemeli.
    cevap, model, arama = calistir([arama_iste(f"sorgu {i}") for i in range(10)], sinir=3)

    assert len(arama.sorgular) == 3
    assert [ayar for ayar, _ in model.cagrilar] == ["any", "auto", "auto", "araçsız"]
    assert cevap.metin == "elimdekilerle cevap"
    # Son çağrıda araç geçmişi yok (her sağlayıcıda geçerli); bulunan pasajlar düz metin olarak soruyla gelir.
    son_istem = model.cagrilar[-1][1]
    assert not any(isinstance(m, ToolMessage) or getattr(m, "tool_calls", None) for m in son_istem)
    assert "sorgu 2 hakkında metin" in son_istem[-1].content and son_istem[-1].content.endswith("(Answer in Turkish.)")


def test_hatali_arguman_aramayi_calistirmaz_hata_modele_doner():
    cevap, model, arama = calistir([
        arama_iste(argumanlar={"soru": "yanlış alan adı"}),
        arama_iste("düzeltilmiş sorgu"),
        AIMessage("cevap"),
    ])

    hata = model.cagrilar[1][1][-1]
    assert isinstance(hata, ToolMessage) and hata.status == "error" and "sorgu" in hata.content
    assert arama.sorgular == ["düzeltilmiş sorgu"]
    assert cevap.metin == "cevap"


def test_ayni_turda_iki_dilde_arama_tek_tur_sayilir():
    cevap, model, arama = calistir([arama_iste("Ante kanunu nedir?", "What is Ante's law?"), AIMessage("cevap")], sinir=1)

    assert arama.sorgular == ["Ante kanunu nedir?", "What is Ante's law?"]
    assert cevap.arama_sayisi == 2
    # Sınır 1 tur olduğu halde iki arama da yapıldı; ardından model cevap verdi, son_cevap'a gerek kalmadı.
    assert [ayar for ayar, _ in model.cagrilar] == ["any", "araçsız"]


def test_bir_turda_en_fazla_iki_arama():
    cevap, _, arama = calistir([arama_iste("bir", "iki", "üç", "dört"), AIMessage("cevap")])
    assert arama.sorgular == ["bir", "iki"]
    assert cevap.arama_sayisi == 2


def test_bozuk_json_hata_olarak_modele_doner():
    cevap, model, arama = calistir([bozuk_json_ile_arama(), arama_iste("Ante kanunu"), AIMessage("cevap")])

    hata = model.cagrilar[1][1][-1]
    assert isinstance(hata, ToolMessage) and hata.tool_call_id == "bozuk" and hata.status == "error"
    assert arama.sorgular == ["Ante kanunu"]
    assert cevap.metin == "cevap"


def test_hep_bozuk_json_gelirse_tur_siniri_yine_isler():
    cevap, model, arama = calistir([bozuk_json_ile_arama() for _ in range(5)], sinir=2)

    assert arama.sorgular == []
    assert [ayar for ayar, _ in model.cagrilar] == ["any", "auto", "araçsız"]
    assert cevap.metin == "elimdekilerle cevap"


def test_bos_cevapta_zincire_duser(monkeypatch):
    zincir = []
    monkeypatch.setattr(ajan, "zincir_cevap_uret", lambda soru, gecmis: zincir.append(soru) or ajan.Cevap("zincir", [], soru, "tr"))
    cevap, _, _ = calistir([arama_iste("Ante"), AIMessage("")])
    assert cevap.metin == "zincir" and zincir == ["Ante kanunu nedir?"]


def test_ayni_parca_iki_kez_gelirse_bir_kez_sayilir():
    cevap, _, _ = calistir([arama_iste("Ante", "Ante"), AIMessage("cevap")])
    assert len(cevap.dokumanlar) == 1


def test_cevap_dili_ret_cumlesi_ve_gecmis_modele_dogru_sirada_gider():
    _, model, _ = calistir(
        [arama_iste("What is Ante's law?"), AIMessage("answer")],
        soru="What is Ante's law?",
        gecmis=["User: Merhaba", "Assistant: Merhaba, nasıl yardımcı olabilirim?"],
    )

    sistem, kullanici, asistan_mesaji, soru = model.cagrilar[0][1]
    assert isinstance(sistem, SystemMessage)
    assert "Write your answer in English" in sistem.content
    assert "There is no information about this question in these sources." in sistem.content
    assert (kullanici.content, asistan_mesaji.content) == ("Merhaba", "Merhaba, nasıl yardımcı olabilirim?")
    assert isinstance(soru, HumanMessage) and soru.content.endswith("(Answer in English.)")


# ---------------------------------------------------------------------------
# Mod seçimi (asistan.py)
# ---------------------------------------------------------------------------
def test_varsayilan_mod_zincir_istenirse_agent(monkeypatch):
    cagrilan = []
    monkeypatch.setattr(asistan, "_MODLAR", {
        "chain": lambda soru, gecmis: cagrilan.append("chain") or ajan.Cevap("z", [], soru, "tr"),
        "agent": lambda soru, gecmis: cagrilan.append("agent") or ajan.Cevap("a", [], soru, "tr"),
    })

    assert asistan.asistana_sor("soru") == "z"
    assert asistan.cevap_uret("soru", mod="agent").metin == "a"
    assert cagrilan == ["chain", "agent"]


def test_bilinmeyen_mod_uygulamayi_baslatmaz(monkeypatch):
    monkeypatch.setenv("ASSISTANT_MODE", "agnet")
    try:
        with pytest.raises(ValueError, match="agnet"):
            importlib.reload(asistan)
    finally:
        monkeypatch.setenv("ASSISTANT_MODE", "chain")
        importlib.reload(asistan)

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

from app import main

GECERLI = {"X-API-Key": "test-anahtari"}
SORU = {"question": "Gingivitis nedir?", "history": []}


@pytest.fixture
def istemci():
    return TestClient(main.app)


@pytest.fixture
def asistan(monkeypatch):
    """asistana_sor yerine geçer: LLM'e ve Azure'a gidilmez, çağrılar kaydedilir."""

    class SahteAsistan:
        def __init__(self):
            self.cagrilar = []
            self.hata = None

        def __call__(self, soru, gecmis=None):
            self.cagrilar.append((soru, gecmis))
            if self.hata:
                raise self.hata
            return "Sahte cevap"

    sahte = SahteAsistan()
    monkeypatch.setattr(main, "asistana_sor", sahte)
    return sahte


# ---------------------------------------------------------------------------
# Başarılı istek
# ---------------------------------------------------------------------------

def test_gecerli_istek_cevap_doner(istemci, asistan):
    yanit = istemci.post("/ask", json={"question": "Gingivitis nedir?", "history": ["User: Merhaba"]},
                         headers=GECERLI)
    assert yanit.status_code == 200
    assert yanit.json() == {"answer": "Sahte cevap"}
    assert asistan.cagrilar == [("Gingivitis nedir?", ["User: Merhaba"])]


def test_history_gonderilmezse_bos_liste(istemci, asistan):
    istemci.post("/ask", json={"question": "Gingivitis nedir?"}, headers=GECERLI)
    assert asistan.cagrilar == [("Gingivitis nedir?", [])]


def test_question_eksikse_422(istemci, asistan):
    yanit = istemci.post("/ask", json={"history": []}, headers=GECERLI)
    assert yanit.status_code == 422
    assert asistan.cagrilar == []


# ---------------------------------------------------------------------------
# Uygulama anahtarı
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("basliklar", [{}, {"X-API-Key": "yanlis-anahtar"}, {"X-API-Key": ""}])
def test_anahtar_yoksa_veya_yanlissa_401(istemci, asistan, basliklar):
    yanit = istemci.post("/ask", json=SORU, headers=basliklar)
    assert yanit.status_code == 401
    assert yanit.json()["detail"] == "Geçersiz veya eksik API anahtarı."
    # Reddedilen istek LLM'e hiç ulaşmaz.
    assert asistan.cagrilar == []


def test_anahtarsiz_istekler_kotayi_tuketmez(istemci, asistan):
    # Anahtar kontrolü rate limit'ten önce: saldırgan anahtarsız isteklerle gerçek kullanıcıyı kilitleyemez.
    for _ in range(10):
        istemci.post("/ask", json=SORU)
    assert istemci.post("/ask", json=SORU, headers=GECERLI).status_code == 200


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------

def test_dakikada_altinci_istek_429(istemci, asistan):
    for _ in range(5):
        assert istemci.post("/ask", json=SORU, headers=GECERLI).status_code == 200

    yanit = istemci.post("/ask", json=SORU, headers=GECERLI)
    assert yanit.status_code == 429
    assert "Retry-After" in yanit.headers
    assert len(asistan.cagrilar) == 5


# ---------------------------------------------------------------------------
# LLM hataları: kullanıcıya mesaj gider ama durum kodu hata olur, böylece mobil uygulama
# mesajı asistan cevabı sanıp sohbet geçmişine kaydetmez.
# ---------------------------------------------------------------------------

def test_gecici_llm_hatasi_503(istemci, asistan):
    asistan.hata = openai.APITimeoutError(request=httpx.Request("POST", "https://test.invalid"))

    yanit = istemci.post("/ask", json=SORU, headers=GECERLI)

    assert yanit.status_code == 503
    assert "tekrar dener misin" in yanit.json()["detail"]
    assert "Retry-After" in yanit.headers


def test_beklenmeyen_hata_500_ve_ic_detay_sizmaz(istemci, asistan):
    asistan.hata = RuntimeError("deployment=gizli-deployment endpoint=https://gizli.example")

    yanit = istemci.post("/ask", json=SORU, headers=GECERLI)

    assert yanit.status_code == 500
    assert yanit.json()["detail"] == "Beklenmeyen bir hata oluştu, lütfen daha sonra tekrar dene."
    assert "gizli" not in yanit.text

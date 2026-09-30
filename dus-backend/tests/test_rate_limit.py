from collections import deque

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import guvenlik
from app.guvenlik import DAKIKA, GUN, _bekleme_suresi, istek_sinirini_uygula, istemci_ip


class SahteSaat:
    """time.monotonic yerine geçer; testte beklemek yerine saat ileri sarılır."""

    def __init__(self):
        self.simdi = 1000.0

    def __call__(self):
        return self.simdi

    def ilerlet(self, saniye):
        self.simdi += saniye


@pytest.fixture
def saat(monkeypatch):
    sahte = SahteSaat()
    monkeypatch.setattr(guvenlik.time, "monotonic", sahte)
    return sahte


def istek(xff=None, istemci="100.100.0.1"):
    # Uygulamanın gördüğü haliyle bir HTTP isteği: istemci adresi ACA ingress proxy'si,
    # gerçek IP X-Forwarded-For'da.
    basliklar = [(b"x-forwarded-for", xff.encode())] if xff else []
    return Request({"type": "http", "headers": basliklar, "client": (istemci, 12345)})


def sinira_takilir(req):
    with pytest.raises(HTTPException) as hata:
        istek_sinirini_uygula(req)
    return hata.value


# ---------------------------------------------------------------------------
# _bekleme_suresi: kayan pencere hesabı
# ---------------------------------------------------------------------------

def test_sinirin_altinda_bekleme_yok():
    assert _bekleme_suresi(deque([0, 1, 2, 3]), simdi=10, sinir=5, pencere=DAKIKA) is None


def test_sinira_ulasinca_ilk_istegin_pencereden_cikmasi_beklenir():
    # 0..4. saniyelerde 5 istek, şimdi 10. saniye: 0. saniyedeki istek 60. saniyede pencereden çıkar.
    assert _bekleme_suresi(deque([0, 1, 2, 3, 4]), simdi=10, sinir=5, pencere=DAKIKA) == 50


def test_pencere_disindaki_istekler_sayilmaz():
    # İlk iki istek 60 saniyeden eski; pencerede sadece 3 istek kalır.
    assert _bekleme_suresi(deque([0, 5, 70, 80, 90]), simdi=100, sinir=5, pencere=DAKIKA) is None


# ---------------------------------------------------------------------------
# istemci_ip: proxy arkasında doğru IP
# ---------------------------------------------------------------------------

def test_x_forwarded_for_yoksa_baglanan_adres():
    assert istemci_ip(istek()) == "100.100.0.1"


def test_x_forwarded_for_en_sagdaki_deger_alinir():
    # Soldaki değeri istemci kendisi yazabilir; en sağdakini proxy ekler.
    assert istemci_ip(istek(xff="6.6.6.6, 1.2.3.4")) == "1.2.3.4"


# ---------------------------------------------------------------------------
# istek_sinirini_uygula: IP başına ve genel sınırlar
# ---------------------------------------------------------------------------

def test_dakikada_bes_istek_kabul_altincisi_429(saat):
    for _ in range(5):
        istek_sinirini_uygula(istek(xff="1.2.3.4"))

    hata = sinira_takilir(istek(xff="1.2.3.4"))
    assert hata.status_code == 429
    assert "Çok fazla soru" in hata.detail
    assert hata.headers["Retry-After"] == "60"


def test_bir_dakika_sonra_tekrar_kabul(saat):
    for _ in range(5):
        istek_sinirini_uygula(istek(xff="1.2.3.4"))
    saat.ilerlet(DAKIKA)
    istek_sinirini_uygula(istek(xff="1.2.3.4"))  # hata fırlatmamalı


def test_bir_ipnin_siniri_digerini_etkilemez(saat):
    for _ in range(5):
        istek_sinirini_uygula(istek(xff="1.2.3.4"))
    istek_sinirini_uygula(istek(xff="5.6.7.8"))  # hata fırlatmamalı


def test_sahte_x_forwarded_for_siniri_asamaz(saat):
    # Saldırgan her istekte soldaki değeri değiştirse de proxy'nin eklediği gerçek IP aynı kalır.
    for i in range(5):
        istek_sinirini_uygula(istek(xff=f"9.9.9.{i}, 1.2.3.4"))
    assert sinira_takilir(istek(xff="9.9.9.99, 1.2.3.4")).status_code == 429


def test_ip_basina_gunluk_sinir(saat):
    # Dakika sınırına takılmadan 20 istek: her 5 istekten sonra bir dakika geçer.
    for i in range(20):
        if i and i % 5 == 0:
            saat.ilerlet(DAKIKA)
        istek_sinirini_uygula(istek(xff="1.2.3.4"))
    saat.ilerlet(DAKIKA)

    hata = sinira_takilir(istek(xff="1.2.3.4"))
    assert "Çok fazla soru" in hata.detail
    # İlk istek günün başında atıldı; o pencereden çıkana kadar beklenir.
    assert int(hata.headers["Retry-After"]) == GUN - 4 * DAKIKA


def test_genel_gunluk_sinir_farkli_iplerden_de_dolar(saat):
    for i in range(30):
        istek_sinirini_uygula(istek(xff=f"10.0.0.{i}"))

    hata = sinira_takilir(istek(xff="10.0.1.1"))
    assert hata.status_code == 429
    assert "Günlük soru kapasitesi doldu" in hata.detail


def test_reddedilen_istek_sayaca_eklenmez(saat):
    for _ in range(5):
        istek_sinirini_uygula(istek(xff="1.2.3.4"))
    for _ in range(3):
        sinira_takilir(istek(xff="1.2.3.4"))
    # Reddedilenler sayılsaydı genel sayaç 8 olurdu.
    assert len(guvenlik._genel_istekler) == 5


def test_bir_gun_sonra_sayaclar_temizlenir(saat):
    istek_sinirini_uygula(istek(xff="1.2.3.4"))
    saat.ilerlet(GUN)
    istek_sinirini_uygula(istek(xff="5.6.7.8"))
    # 24 saattir istek atmayan IP'nin kaydı bellekte tutulmaz.
    assert "1.2.3.4" not in guvenlik._ip_istekleri
    assert len(guvenlik._genel_istekler) == 1
